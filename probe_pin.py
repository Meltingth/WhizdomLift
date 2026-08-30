"""
Live pin probe - prove whether an Arduino input pin and its wiring work.

    python probe_pin.py                 watch every pin
    python probe_pin.py 16 17 19 20     watch just these

Touch a jumper from any GND terminal on the DNMEGA1 to the signal terminal you
want to test; the pin behind it is named here the moment it registers.

Safe by construction: the pin is an input with a ~30k pullup, so grounding it
draws about 0.15 mA. Nothing is ever driven.

    pin reacts        the pin, its screw terminal and the track between them
                      are sound. If that line still shows nothing while the
                      lift runs, the fault is upstream - at the relay module
                      or the controller, not here.
    nothing happens   that pin or its wiring to the terminal is dead.

Two details that matter:

  - A contact must hold HOLD_MS to count. Lift 2's status lines dip LOW for
    2-4ms continuously from induced mains hum; without the threshold the screen
    would fill with phantom hits and a real touch would be lost among them.

  - The hold is timed on the PC clock, not the board's. The sketch only emits a
    line when something changes, so a pin held steadily low produces one line
    and then silence - waiting for a further board timestamp would mean waiting
    forever.
"""
import re
import sys
import time

import serial

from lift_decode import arm_watch

PORT = "COM3"
BAUD = 115200
DIG_FIRST = 2
HOLD_S = 0.12           # longer than mains-hum blips, far shorter than a touch

NAMES = {24: "VS2", 25: "VS3", 26: "VS4", 27: "VS5", 28: "VS6", 29: "VS7",
         16: "RUNNING", 17: "SAFETY", 19: "UP", 20: "DN"}
ST_RE = re.compile(r"^ST (\d+) ([0-9A-Fa-f]+)")


def label(pin):
    return f"D{pin}" + (f" ({NAMES[pin]})" if pin in NAMES else "")


watch = {int(a) for a in sys.argv[1:] if a.isdigit()}

print(f"opening {PORT} ...")
ser = serial.Serial(PORT, BAUD, timeout=0.1)
try:
    arm_watch(ser)
except serial.SerialException as e:
    raise SystemExit(f"could not arm the board: {e}")

print("armed.\n")
print("  Touch a GND jumper to the terminal you want to test.")
print("  Watching: " + (", ".join(label(p) for p in sorted(watch)) if watch
                        else "every pin"))
print(f"  A contact must hold {HOLD_S * 1000:.0f}ms to count, so mains hum is ignored.")
print("  Ctrl-C to stop.\n" + "-" * 62)

low_since = {}          # pin -> PC clock when it last went low
announced = set()
buf = b""

try:
    while True:
        chunk = ser.read(256)
        now = time.time()
        if chunk:
            buf += chunk
            while b"\n" in buf:
                raw, buf = buf.split(b"\n", 1)
                m = ST_RE.match(raw.decode("utf-8", "replace").strip())
                if not m:
                    continue
                mask = int(m.group(2), 16)
                for i in range(52):
                    pin = DIG_FIRST + i
                    if watch and pin not in watch:
                        continue
                    if not (mask >> i) & 1:          # contact closed
                        low_since.setdefault(pin, now)
                    else:
                        low_since.pop(pin, None)
                        announced.discard(pin)       # ready to report again

        for pin, since in sorted(low_since.items()):
            if pin not in announced and now - since >= HOLD_S:
                announced.add(pin)
                print(f"  {time.strftime('%H:%M:%S')}  CONTACT on {label(pin)}"
                      f"   held {now - since:.2f}s  -> this pin and its wiring work")
except KeyboardInterrupt:
    print("\nstopped")
finally:
    ser.close()
