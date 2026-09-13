"""
Long-running capture of the lift's signal lines. Runs until told to stop.

    python log_lift.py COM5 2          capture Lift 2 -> capture_lift_2.log
    python log_lift.py COM3 3          capture Lift 3 -> capture_lift_3.log

Stop it by deleting nothing and creating a file called STOP_CAPTURE next to the
log, or just kill the process - every line is flushed as it arrives, so the log
is complete right up to the moment it dies.

Each state change is written as:

    <wall clock>  <board ms>  <52-bit mask hex>  <pins currently closed>

Recovers on its own if the USB link drops: it reopens the port, re-arms watch
mode and carries on appending, noting the gap in the log.
"""
import os
import random
import re
import sys
import time
from datetime import datetime

# pyserial may live in the user profile, which a process started by the
# Scheduled Task cannot read - it dies on "import serial" before writing a
# line. A copy next to this file on D: is reachable from every context:
#     pip install --target vendor pyserial
_vendor = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor")
if os.path.isdir(_vendor) and _vendor not in sys.path:
    sys.path.insert(0, _vendor)

import serial
from serial.tools import list_ports

# usage: python log_lift.py PORT [LIFT] [logfile]
#     e.g. python log_lift.py COM5 2            -> capture_lift_2.log
#          python log_lift.py COM7 2 --listen  -> one-way RS485 link
#          (the old letters A-E still work: A=Lift 3, B=Lift 1,
#           C=Lift 2, D=Lift 4, E=Lift 5)
#
# One process per board. Name the LIFT, not the port: boards get swapped
# between sessions and Windows reassigns COM numbers, so a port-named log
# silently appends one lift's data onto another's. The lift name is stamped
# into the file and re-checked on every open, which turns that from a silent
# corruption into a refusal to start.
#
# All loggers share one STOP_CAPTURE file, so creating it stops every capture.
from lift_decode import lift_id, lift_label     # single source of lift naming

# --listen: never transmit, just record. Required on a one-way RS485 link
# where the transceiver is strapped transmit-only and the board cannot hear us.
LISTEN_ONLY = "--listen" in sys.argv

# --follow: if the port goes away, find this lift again by the identity its
# board announces, whatever COM number Windows has handed it this time. See
# reacquire() for why that is safe and where it deliberately refuses to guess.
FOLLOW = "--follow" in sys.argv
_args = [a for a in sys.argv[1:] if not a.startswith("--")]

PORT = _args[0].upper() if _args else "COM3"
LIFT = lift_id(_args[1]) if len(_args) > 1 else None
BAUD = 115200
DIG_FIRST = 2
_here = os.path.dirname(os.path.abspath(__file__))
if LIFT:
    _default = f"capture_lift_{LIFT}.log"
else:
    _default = f"capture_lift_{PORT}.log"
LOG = _args[2] if len(_args) > 2 else os.path.join(_here, _default)
STOP = os.path.join(os.path.dirname(os.path.abspath(LOG)), "STOP_CAPTURE")
OWNER = f"# lift: {LIFT}" if LIFT else None


def check_owner():
    """Refuse to append one lift's capture onto another lift's log.

    Compare normalised ids rather than raw text. Logs recorded before the
    letters were mapped onto building numbers carry the old spelling -
    capture_lift_1.log is stamped "# lift: B" - and B and 1 are the same lift.
    A literal string compare reads its own history as a different lift and
    refuses to record the one the file belongs to, which would land at the
    worst possible moment: the first capture after a repair.
    """
    if not (LIFT and os.path.exists(LOG)):
        return
    with open(LOG, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("# lift:"):
                stamped = line.strip()[len("# lift:"):].strip()
                if lift_id(stamped) != LIFT:
                    raise SystemExit(
                        f"REFUSING TO START\n"
                        f"  {os.path.basename(LOG)} already belongs to "
                        f"{lift_label(stamped)}, not {lift_label(LIFT)}.\n"
                        f"  Pick a different lift name or move the old file "
                        f"aside.")
                return


def closed_pins(mask):
    """Pins reading LOW - i.e. relay contacts currently closed."""
    return [DIG_FIRST + i for i in range(52) if not (mask >> i) & 1]


BOOT_WAIT = 3.0     # bootloader holds the line for ~2s after the port opens

# AVR millis() is a 32-bit unsigned counter, so it rolls over to 0 after
# 49.7 days. On a permanently installed board that is a routine event, not a
# reboot, and it must not be reported as one.
MILLIS_WRAP = 2 ** 32

# A board that really did restart has just booted, so its uptime is small. The
# sketch emits a baseline at boot and a heartbeat every 60s, so we hear from a
# restarted board well inside this window. Anything older than it is a board
# that has been running for a while, whatever the wall clock suggests.
FRESH_BOOT_MS = 120_000


def _set_mode(ser, cmd, want, opposite, tries=4):
    """Send a toggle command until the board confirms the state we want.

    These are toggles, not absolute settings, so firing once and hoping is not
    good enough: if the board was already in the target state the command flips
    it the wrong way. Read the confirmation line back and toggle again if it
    says the opposite.
    """
    for _ in range(tries):
        ser.reset_input_buffer()
        ser.write(cmd)
        ser.flush()
        end = time.time() + 2.5
        buf = b""
        while time.time() < end:
            buf += ser.read(256)
            if want in buf:
                return True
            if opposite in buf:
                break              # toggled the wrong way - go round again
        time.sleep(0.2)
    return False


class WrongBoard(Exception):
    """The board on this port says it belongs to a different lift."""

    def __init__(self, got):
        super().__init__("board says it is Lift %s" % got)
        self.got = got


IDENT_S = 35.0          # must exceed the board's 30s identity beacon


def open_quiet(port, baud=BAUD, timeout=0.5):
    """Open a port with DTR and RTS already low.

    Lesson 6.17 measured a board resetting on the first open *despite*
    dtr=False, because pyserial can only lower those lines after the driver
    has opened the handle and asserted them. Setting them on an unopened
    Serial and letting open() apply them is the one chance to avoid that. On
    the RS485 dongles it is moot - they have no reset line to the Arduino -
    but a search must not be the thing that reboots a board it is only
    looking at.

    UNVERIFIED on a directly-attached Arduino: there is no USB-attached board
    on this machine to test it against, so treat it as a precaution rather
    than a guarantee, and keep --follow for RS485 dongles.
    """
    ser = serial.Serial()
    ser.port = port
    ser.baudrate = baud
    ser.timeout = timeout
    ser.dtr = False
    ser.rts = False
    ser.open()
    return ser


def identify(port, secs=IDENT_S):
    """Listen to one port and ask what it is. Transmits nothing.

    Returns (state, lift), state being one of:
      identified  the board announced LIFT=<lift>
      claimed     another capture holds this port - never touched
      gone        the port vanished between listing it and opening it
      quiet       traffic, but no identity within the beacon interval
      silent      not one byte
      error       anything else, described in the second value

    Windows opens a COM port exclusively, so a port a logger is recording on
    refuses us with PermissionError while a port that has gone away refuses
    with FileNotFoundError. Those two being distinguishable is what makes a
    search safe to run beside four live captures: it can never read a held
    port's identity, and it can never steal one either.
    """
    try:
        ser = open_quiet(port)
    except (serial.SerialException, OSError) as e:
        txt = str(e)
        if "PermissionError" in txt or "Access is denied" in txt:
            return "claimed", None
        if "FileNotFoundError" in txt or "cannot find" in txt:
            return "gone", None
        return "error", txt[:80]
    try:
        end = time.time() + secs
        buf = b""
        while time.time() < end:
            buf += ser.read(512)
            for line in buf.decode("utf-8", "replace").splitlines():
                if line.startswith("FW "):
                    m = re.search(r"LIFT=(\d+)", line)
                    if m and m.group(1) != "0":
                        return "identified", m.group(1)
        return ("quiet" if buf else "silent"), None
    finally:
        try:
            ser.close()
        except Exception:
            pass


def candidate_ports():
    return [p.device for p in list_ports.comports()
            if "CH340" in (p.description or "") or "USB" in (p.description or "")]


def reacquire(lift, log=None, probe=identify):
    """Find the port this lift is on now. Returns a port, or None to retry.

    Why this is not the silent self-repair CLAUDE.md 9.6 warns against: that
    warning is about a logger *guessing* a replacement after finding a foreign
    board, where a deliberate re-plug and a dead dongle look identical. This
    guesses nothing. It attaches only to a port whose board has just announced
    this exact lift id - the same proof listen_check demands before writing a
    first line. The identity is the key; the COM number was only ever a handle.

    Three refusals keep it honest:
      * a port announcing a different lift is passed over, never adopted;
      * a port another logger holds is skipped, so two captures cannot fight;
      * two ports announcing the SAME lift stop the process outright. That is
        two boards flashed with one id - a build mistake - and taking either
        would put one lift's data in another lift's log, the exact corruption
        every identity check here exists to prevent.

    Ports are probed in random order so four loggers searching at once do not
    lock-step onto the same one, and each probe releases immediately, so a
    port that reads "claimed" this pass is simply retried on the next.
    """
    ports = candidate_ports()
    random.shuffle(ports)
    seen, matches = {}, []
    for port in ports:
        state, val = probe(port)
        seen[port] = val if state == "identified" else state
        if state == "identified" and val == lift:
            matches.append(port)

    summary = " ".join("%s=%s" % kv for kv in sorted(seen.items())) or "no ports"
    if log is not None:
        log.write("--- searching for Lift %s: %s %s ---%s"
                  % (lift, summary, datetime.now().strftime("%H:%M:%S"),
                     chr(10)))

    if len(matches) > 1:
        raise SystemExit(
            "\nSTOPPING - %d ports all claim to be Lift %s: %s\n"
            "  Two boards carry the same -DLIFT_ID. Taking either one would "
            "put this lift's data somewhere it does not belong.\n"
            "  Reflash them with distinct ids, then restart this capture."
            % (len(matches), lift, ", ".join(matches)))
    if matches:
        return matches[0]
    print("\n  Lift %s is not on any port yet (%s)" % (lift, summary))
    return None


def listen_check(ser, seconds=75.0, want_lift=None):
    """Confirm the board is already reporting, without sending anything.

    Replaces arm() on a one-way link. The point of arm() was never the
    commands themselves but the verification - a capture that silently never
    started is the failure in lesson 6.2. Here the equivalent proof is simply
    that ST lines turn up on their own; the sketch arms itself at boot.

    The wait must exceed the board's heartbeat interval. A parked lift changes
    nothing, so the only traffic is that heartbeat every 60s; a shorter window
    reports a perfectly good link as dead and sends the reader off to check
    A/B polarity for a fault that does not exist. Waiting 75s to fail is slow,
    but a wrong answer costs far more than the wait.
    """
    ser.dtr = False
    ser.rts = False
    time.sleep(0.2)
    ser.reset_input_buffer()
    end = time.time() + seconds
    buf = b""
    seen_st = False
    while time.time() < end:
        buf += ser.read(512)
        text = buf.decode("utf-8", "replace")

        # Settle identity BEFORE a single line is written. The board repeats it
        # every 30s, so waiting for it costs half a minute once; not waiting
        # costs up to half a minute of one lift's data landing in another
        # lift's log, which is the whole failure this check exists to stop.
        for line in text.splitlines():
            if line.startswith("FW ") and want_lift:
                m = re.search(r"LIFT=(\d+)", line)
                if m:
                    got = m.group(1)
                    if got == "0":
                        print("  WARNING: firmware built without -DLIFT_ID; "
                              "it cannot say which lift this is")
                        return True
                    if got != want_lift:
                        # Raised, not exited: without --follow main() turns
                        # this straight back into the same fatal message, and
                        # with it the search decides what to do instead.
                        raise WrongBoard(got)
                    print(f"  board confirms it is Lift {got}")
                    return True
            if line.startswith("ST "):
                seen_st = True

        # An older board sends no identity at all. Do not lock it out - but do
        # not pretend it was verified either.
        if seen_st and time.time() > end - (seconds - 40):
            print("  note: no lift id from this board (firmware predates "
                  "1.2.0) - cannot confirm which lift it is")
            return True

    raise serial.SerialException(
        f"no ST lines in {seconds:.0f}s - longer than the board's 60s "
        f"heartbeat, so this is a real fault rather than a quiet lift. "
        f"Check the A/B pair is not swapped, that DE and RE are tied high, "
        f"and that the board has power.")


def arm(ser):
    """Put the sketch into watch mode, and verify it actually took.

    Opening the port resets the board, and the bootloader then swallows
    everything for about two seconds before the sketch starts. Commands sent
    inside that window are simply lost, so wait it out first - and confirm,
    because a capture that silently never armed is worse than one that fails
    loudly.
    """
    ser.dtr = False               # do not reset it again from here on
    ser.rts = False
    time.sleep(0.2)
    ser.reset_input_buffer()
    time.sleep(BOOT_WAIT)         # let the bootloader hand over to the sketch

    ok_a = _set_mode(ser, b"a", b"analog reporting OFF", b"analog reporting ON")
    ok_w = _set_mode(ser, b"w", b"watch mode ON", b"watch mode OFF")
    if not ok_w:
        raise serial.SerialException(
            "board never confirmed watch mode - not capturing anything")
    ser.write(b"e")               # baseline state, so the log starts with one
    ser.flush()
    return ok_a, ok_w


def main():
    global PORT                      # --follow may move this capture's port
    # Every logger shares this file, so starting five at once has five of them
    # racing between the exists() and the remove(). The loser used to die at
    # startup with FileNotFoundError - and a capture that never starts is the
    # failure this whole file is built to avoid.
    try:
        os.remove(STOP)
    except FileNotFoundError:
        pass

    check_owner()

    # Fail loudly on a port that does not exist. The reconnect loop below is
    # meant for a USB link that drops mid-capture; letting a typo'd port fall
    # into it produces a process that looks alive for hours and records nothing.
    available = [p.device for p in list_ports.comports()]
    if PORT == "AUTO" or (FOLLOW and PORT not in available):
        # Under --follow the COM number is a handle, not an identity, so a
        # missing one is not a reason to refuse to start: ask the boards who
        # they are instead. This is also what survives a PC reboot, where
        # every number may come back different.
        if not FOLLOW:
            raise SystemExit(
                "port 'auto' only works with --follow, which is the part that "
                "knows how to find a lift by the identity it announces.")
        if not LIFT:
            raise SystemExit("--follow needs a lift number to search for.")
        print(f"searching for Lift {LIFT} by identity "
              f"(~{IDENT_S:.0f}s per port, transmitting nothing)")
        found = None
        while found is None:
            if os.path.exists(STOP):
                raise SystemExit("STOP_CAPTURE exists - not starting.")
            found = reacquire(LIFT)
            if found is None:
                time.sleep(3)
        print(f"  Lift {LIFT} is on {found}")
        PORT = found
    elif PORT not in available:
        raise SystemExit(
            f"{PORT} is not present.\n"
            f"  ports available now: {', '.join(available) if available else '(none)'}\n"
            f"  check the USB cable, then rerun with the right port,\n"
            f"  or add --follow to let this capture find Lift {LIFT} itself.")
    # Leave a PID behind. A capture started by the Scheduled Task reports an
    # EMPTY command line to any query from an ordinary shell, so the watchdog
    # cannot recognise it and would start a second logger on the same lift -
    # the corruption 6.8 exists to prevent. Process EXISTENCE is visible even
    # when the command line is not, so the pid is the identity that survives
    # the privilege boundary. Best effort: a stale file is handled by checking
    # that the pid is alive, not by trusting the file.
    PIDFILE = os.path.join(os.path.dirname(os.path.abspath(LOG)),
                           f"capture_lift_{LIFT}.pid") if LIFT else None
    if PIDFILE:
        try:
            with open(PIDFILE, "w", encoding="utf-8") as fh:
                fh.write(str(os.getpid()))
        except OSError:
            pass

    log = open(LOG, "a", encoding="utf-8", buffering=1)   # line buffered
    if OWNER:
        log.write(f"{OWNER}\n")
    log.write(f"\n===== capture started {datetime.now():%Y-%m-%d %H:%M:%S}"
              f"  lift={LIFT or '?'}  port={PORT} =====\n")
    print(f"{lift_label(LIFT) if LIFT else '(unnamed lift)'} on {PORT}")
    print(f"logging to {LOG}")
    print(f"stop by creating {STOP}\n")

    changes = 0
    started = time.time()
    last_report = time.time()
    last_beat = time.time()
    beats = 0
    buf = b""
    ser = None
    rejects = 0           # malformed lines; must stay 0 on a good link
    last_ms = None        # board clock, to notice restarts
    last_wall = 0.0       # PC clock at that sample, to compare against
    armed_once = False    # has a capture ever actually started on this port?
    first_fails = 0
    force_scan = False    # a foreign board answered here; do not retry this port
    HEARTBEAT_S = 60      # ask the board to restate itself this often

    while not os.path.exists(STOP):
        try:
            # Windows numbers CH340 ports by which socket they sit in, so a
            # dongle put back in a different socket comes up under a different
            # name. Without this, the loop below retries a number that will
            # never return and records nothing, looking healthy the whole time.
            if ser is None and FOLLOW and (armed_once or force_scan):
                here = [p.device for p in list_ports.comports()]
                if force_scan or PORT not in here:
                    found = reacquire(LIFT, log)
                    if found is None:
                        time.sleep(3)
                        continue
                    if found != PORT:
                        log.write(f"--- rebound to {found} (was {PORT}) "
                                  f"{datetime.now():%H:%M:%S} ---" + chr(10))
                        print(f"\n  Lift {LIFT} moved: {PORT} -> {found}")
                        PORT = found
                    force_scan = False

            if ser is None:
                ser = open_quiet(PORT)
                if LISTEN_ONLY:
                    listen_check(ser, want_lift=LIFT)
                else:
                    arm(ser)
                armed_once = True
                mode = "listening (one-way)" if LISTEN_ONLY else "armed, watch mode confirmed"
                log.write(f"--- {mode} {datetime.now():%H:%M:%S} ---" + chr(10))
                print("listening - board is reporting on its own"
                      if LISTEN_ONLY else
                      "armed - watch mode confirmed by the board")

            chunk = ser.read(512)
            if chunk:
                buf += chunk
                while b"\n" in buf:
                    raw, buf = buf.split(b"\n", 1)
                    line = raw.decode("utf-8", "replace").strip()

                    # Record which build is talking. On a one-way link this is
                    # the only chance to learn it, and with five lifts upgraded
                    # at different times the log has to answer that on its own.
                    if line.startswith("FW "):
                        log.write(f"--- {line} "
                                  f"{datetime.now():%H:%M:%S} ---" + chr(10))
                        print(f"  board reports: {line}")

                        # The board names the lift it belongs to; check it
                        # against the one we were told to record. Five CH340
                        # dongles carry no serial numbers, so Windows names
                        # their ports by which socket they occupy - swap two
                        # and one lift's data lands in another's log with
                        # nothing to show for it. Labelling the stream is not
                        # enough; the mismatch has to stop the capture.
                        m = re.search(r"LIFT=(\d+)", line)
                        if m and LIFT:
                            got = m.group(1)
                            if got == "0":
                                print("  WARNING: firmware was built without "
                                      "-DLIFT_ID, so it cannot confirm which "
                                      "lift this is")
                            elif got != LIFT:
                                raise WrongBoard(got)
                        elif LIFT:
                            print("  note: firmware predates lift ids, "
                                  "cannot verify which board this is")
                        continue

                    if not line.startswith("ST "):
                        continue
                    parts = line.split()
                    # Validate before trusting. A USB cable either delivers a
                    # byte or does not; RS485 can hand over a corrupted one, and
                    # a mask short by a digit still parses as valid hex while
                    # shifting every bit - silently wrong data rather than an
                    # error. Length and character set are checked, and the
                    # reject rate is reported: on a point-to-point link it
                    # should be exactly zero.
                    if len(parts) != 3 or len(parts[2]) != 13:
                        rejects += 1
                        continue
                    try:
                        mask = int(parts[2], 16)
                    except ValueError:
                        rejects += 1
                        continue
                    ms = parts[1]

                    # Spot a restart - a reflash, a power blip, someone
                    # pressing reset. Worth marking: the analysis tools split
                    # their timeline on that seam, and on the Gateway it tells
                    # an upgrade apart from a failing link.
                    #
                    # Testing only for the clock going backwards is not enough.
                    # Two reboots close together both come back near zero, so
                    # the second one lands on a value no lower than the first:
                    # this log has 18:57:20 and 18:57:24 both at ms 89, four
                    # seconds apart, and the backward test saw nothing. A board
                    # returning on a slightly higher value slips through the
                    # same way.
                    #
                    # Between two ST lines the board's millis() advances by the
                    # real elapsed time, so it should track the PC clock. When
                    # far less board time passed than wall time, the board's
                    # clock was reset. Delivery can bunch lines up, but that
                    # skews the other way - wall time short, board time long -
                    # so the test stays one-sided and will not fire on it.
                    # Two guards on top of the two rules, both for false
                    # positives that only show up on a Gateway running five
                    # loggers for months.
                    #
                    # The wall-clock rule compares board time against real time
                    # measured when a line is PROCESSED, not when it arrived.
                    # If this reader is descheduled for a few seconds while the
                    # board keeps emitting, the first line of the backlog looks
                    # exactly like a reset: little board time, lots of wall
                    # time. Bunching protects the lines inside the burst, not
                    # the one that opens it. A board that truly restarted has a
                    # small uptime though, and a stalled reader cannot make the
                    # board's uptime small - so gate on that.
                    #
                    # And millis() rolls over to 0 every 49.7 days, which the
                    # backwards test reads as a reboot. On an installed board
                    # that is routine. Still marked, because the analysers split
                    # their timeline wherever board time drops, but named for
                    # what it is so nobody goes hunting for a power fault.
                    ms_i = int(ms)
                    wall_now = time.time()
                    restarted = reason = None
                    wrapped = False
                    if last_ms is not None:
                        wall_ms = (wall_now - last_wall) * 1000
                        if ms_i < last_ms:
                            if (last_ms > MILLIS_WRAP - FRESH_BOOT_MS
                                    and ms_i < FRESH_BOOT_MS):
                                wrapped = True
                            else:
                                restarted, reason = True, "clock went backwards"
                        elif (wall_ms > 2000 and ms_i < FRESH_BOOT_MS
                                and (ms_i - last_ms) < wall_ms * 0.5):
                            restarted = True
                            reason = (f"board advanced {ms_i - last_ms}ms "
                                      f"while {wall_ms:.0f}ms of real time passed")
                    if restarted:
                        log.write(f"--- board restarted ({reason}: {last_ms} -> "
                                  f"{ms_i}) {datetime.now():%H:%M:%S} ---" + chr(10))
                        print(chr(10) + "  board restarted at "
                              + datetime.now().strftime("%H:%M:%S")
                              + " - " + reason)
                    elif wrapped:
                        log.write(f"--- board clock wrapped, not a restart "
                                  f"(49.7-day millis() overflow: {last_ms} -> "
                                  f"{ms_i}) {datetime.now():%H:%M:%S} ---"
                                  + chr(10))
                        print(chr(10) + "  board clock wrapped at "
                              + datetime.now().strftime("%H:%M:%S")
                              + " - 49.7-day millis() overflow, not a restart")
                    last_ms, last_wall = ms_i, wall_now
                    pins = closed_pins(mask)
                    stamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                    log.write(f"{stamp}  {ms:>10}  {parts[2]}  "
                              f"{','.join(f'D{p}' for p in pins) or '-'}\n")
                    changes += 1

            # A heartbeat turns "nothing happened" into positive evidence: the
            # board answers with its current state, so an idle lift still
            # leaves a trail and a dead link becomes obvious immediately.
            if (not LISTEN_ONLY and ser is not None
                    and time.time() - last_beat >= HEARTBEAT_S):
                ser.write(b"e")
                ser.flush()
                beats += 1
                last_beat = time.time()

            if time.time() - last_report >= 15:
                mins = (time.time() - started) / 60
                print(f"\r  {mins:6.1f} min   {changes:6d} lines   "
                      f"{beats} beats   {rejects} rejected   ", end="", flush=True)
                last_report = time.time()

        except WrongBoard as e:
            # Somebody moved the plugs. Which board is on which port changed;
            # which lift this capture belongs to did not.
            try:
                if ser:
                    ser.close()
            except Exception:
                pass
            ser = None
            log.write(f"--- wrong board on {PORT}: it says Lift {e.got}, this "
                      f"capture is Lift {LIFT} {datetime.now():%H:%M:%S} ---"
                      + chr(10))
            if not FOLLOW:
                raise SystemExit(
                    "STOPPING - wrong board on this port." + chr(10) +
                    f"  recording as Lift {LIFT}, but the board on {PORT} "
                    f"says it is Lift {e.got}." + chr(10) +
                    "  Check which dongle is in which USB socket, or rerun "
                    "with --follow to let this capture find its own board.")
            print(f"\n  {PORT} now carries Lift {e.got} - "
                  f"going to look for Lift {LIFT}")
            force_scan = True
            time.sleep(1)

        except (serial.SerialException, OSError, ValueError) as e:
            log.write(f"--- link lost {datetime.now():%H:%M:%S}: {e} ---\n")
            try:
                if ser:
                    ser.close()
            except Exception:
                pass
            ser = None
            # Retry forever only once a capture has actually worked - that is
            # the USB-glitch case worth surviving. Failing before the first
            # successful arm means something is wrong with the setup, and
            # retrying silently would just hide it.
            if not armed_once:
                first_fails += 1
                if first_fails >= 3:
                    raise SystemExit(
                        f"\nNever managed to arm {PORT} after 3 tries: {e}\n"
                        f"  Is the IODebug sketch loaded on this board?\n"
                        f"  Is another program holding the port?")
                print(f"\n  cannot arm {PORT} ({e}) - retry {first_fails}/3")
            else:
                print(f"\n  link lost ({e}) - retrying in 3 s")
            time.sleep(3)

    if ser:
        ser.close()
    mins = (time.time() - started) / 60
    log.write(f"===== capture stopped {datetime.now():%Y-%m-%d %H:%M:%S}, "
              f"{changes} changes in {mins:.1f} min, "
              f"{rejects} rejected =====" + chr(10))
    log.close()
    if PIDFILE:
        try:
            os.remove(PIDFILE)
        except OSError:
            pass
    print(f"\n\nstopped: {changes} state changes over {mins:.1f} minutes")
    if rejects:
        pct = 100 * rejects / max(changes + rejects, 1)
        print(f"WARNING: {rejects} malformed lines rejected ({pct:.2f}%) - "
              f"check termination, wiring and baud rate")
    print(f"log: {LOG}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\ninterrupted")
