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
import sys
import time
from datetime import datetime

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


def listen_check(ser, seconds=75.0):
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
    while time.time() < end:
        buf += ser.read(512)
        if b"\nST " in buf or buf.startswith(b"ST "):
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
    if os.path.exists(STOP):
        os.remove(STOP)

    check_owner()

    # Fail loudly on a port that does not exist. The reconnect loop below is
    # meant for a USB link that drops mid-capture; letting a typo'd port fall
    # into it produces a process that looks alive for hours and records nothing.
    available = [p.device for p in list_ports.comports()]
    if PORT not in available:
        raise SystemExit(
            f"{PORT} is not present.\n"
            f"  ports available now: {', '.join(available) if available else '(none)'}\n"
            f"  check the USB cable, then rerun with the right port.")
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
    HEARTBEAT_S = 60      # ask the board to restate itself this often

    while not os.path.exists(STOP):
        try:
            if ser is None:
                ser = serial.Serial(PORT, BAUD, timeout=0.5)
                if LISTEN_ONLY:
                    listen_check(ser)
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
