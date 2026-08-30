"""
Long-running capture of the lift's signal lines. Runs until told to stop.

    python log_lift.py                 log to capture_lift.log
    python log_lift.py mylog.log       log somewhere else

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
#     e.g. python log_lift.py COM5 C        -> capture_lift_C.log
#
# One process per board. Name the LIFT, not the port: boards get swapped
# between sessions and Windows reassigns COM numbers, so a port-named log
# silently appends one lift's data onto another's. The lift name is stamped
# into the file and re-checked on every open, which turns that from a silent
# corruption into a refusal to start.
#
# All loggers share one STOP_CAPTURE file, so creating it stops every capture.
PORT = sys.argv[1].upper() if len(sys.argv) > 1 else "COM3"
LIFT = sys.argv[2].upper() if len(sys.argv) > 2 else None
BAUD = 115200
DIG_FIRST = 2
_here = os.path.dirname(os.path.abspath(__file__))
if LIFT:
    _default = "capture_lift.log" if LIFT == "A" else f"capture_lift_{LIFT}.log"
else:
    _default = "capture_lift.log" if PORT == "COM3" else f"capture_lift_{PORT}.log"
LOG = sys.argv[3] if len(sys.argv) > 3 else os.path.join(_here, _default)
STOP = os.path.join(os.path.dirname(os.path.abspath(LOG)), "STOP_CAPTURE")
OWNER = f"# lift: {LIFT}" if LIFT else None


def check_owner():
    """Refuse to append one lift's capture onto another lift's log."""
    if not (OWNER and os.path.exists(LOG)):
        return
    with open(LOG, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("# lift:"):
                if line.strip() != OWNER:
                    raise SystemExit(
                        f"REFUSING TO START\n"
                        f"  {os.path.basename(LOG)} already belongs to "
                        f"{line.strip()[8:]}, not {LIFT}.\n"
                        f"  Pick a different lift name or move the old file "
                        f"aside.")
                return


def closed_pins(mask):
    """Pins reading LOW - i.e. relay contacts currently closed."""
    return [DIG_FIRST + i for i in range(52) if not (mask >> i) & 1]


BOOT_WAIT = 3.0     # bootloader holds the line for ~2s after the port opens


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
    print(f"lift {LIFT or '(unnamed)'} on {PORT}")
    print(f"logging to {LOG}")
    print(f"stop by creating {STOP}\n")

    changes = 0
    started = time.time()
    last_report = time.time()
    last_beat = time.time()
    beats = 0
    buf = b""
    ser = None
    armed_once = False    # has a capture ever actually started on this port?
    first_fails = 0
    HEARTBEAT_S = 60      # ask the board to restate itself this often

    while not os.path.exists(STOP):
        try:
            if ser is None:
                ser = serial.Serial(PORT, BAUD, timeout=0.5)
                arm(ser)
                armed_once = True
                log.write(f"--- armed, watch mode confirmed "
                          f"{datetime.now():%H:%M:%S} ---\n")
                print("armed - watch mode confirmed by the board")

            chunk = ser.read(512)
            if chunk:
                buf += chunk
                while b"\n" in buf:
                    raw, buf = buf.split(b"\n", 1)
                    line = raw.decode("utf-8", "replace").strip()
                    if not line.startswith("ST "):
                        continue
                    parts = line.split()
                    if len(parts) != 3:
                        continue
                    ms, mask = parts[1], int(parts[2], 16)
                    pins = closed_pins(mask)
                    stamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                    log.write(f"{stamp}  {ms:>10}  {parts[2]}  "
                              f"{','.join(f'D{p}' for p in pins) or '-'}\n")
                    changes += 1

            # A heartbeat turns "nothing happened" into positive evidence: the
            # board answers with its current state, so an idle lift still
            # leaves a trail and a dead link becomes obvious immediately.
            if ser is not None and time.time() - last_beat >= HEARTBEAT_S:
                ser.write(b"e")
                ser.flush()
                beats += 1
                last_beat = time.time()

            if time.time() - last_report >= 15:
                mins = (time.time() - started) / 60
                print(f"\r  {mins:6.1f} min   {changes:6d} lines   "
                      f"{beats} heartbeats   ", end="", flush=True)
                last_report = time.time()

        except (serial.SerialException, OSError) as e:
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
              f"{changes} changes in {mins:.1f} min =====\n")
    log.close()
    print(f"\n\nstopped: {changes} state changes over {mins:.1f} minutes")
    print(f"log: {LOG}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\ninterrupted")
