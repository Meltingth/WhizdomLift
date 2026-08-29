"""
Live probe: prove whether an Arduino input pin actually works.

    python probe_pin.py

Touch a jumper from any GND terminal to a signal terminal on the DNMEGA1, and
this announces which Arduino pin just went LOW. Safe by construction - the pin
is an input with a ~30k pullup, so grounding it sources about 0.15mA.

    pin reacts       the pin, the screw terminal and the track between them are
                     all fine; if that line never goes low during lift運行 then
                     the lift controller is simply not asserting it
    nothing happens  that pin or its wiring is dead - a real fault worth chasing

Reads the capture log rather than the serial port, so it runs happily while
log_lift.py keeps recording. Nothing is stopped and no data is lost.
"""
import os
import re
import sys
import time

LOG = sys.argv[1] if len(sys.argv) > 1 else \
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "capture_lift.log")

# Pins already accounted for - anything else appearing is news.
KNOWN = {
    25: "VS2", 26: "VS3", 27: "VS4", 28: "VS5", 29: "VS6",
    16: "RUNNING", 17: "SAFETY", 19: "UP", 20: "DN", 24: "STROBE",
}

LINE_RE = re.compile(r"^(\d\d:\d\d:\d\d\.\d+)\s+\d+\s+[0-9A-Fa-f]+\s+(\S*)")

print("Watching for any pin that has not been seen before.\n")
print("  Touch a GND jumper to the terminal you believe carries VS7,")
print("  FIRE or FIRE RETURN. The pin behind it will be named here.\n")
print("  Ctrl-C to stop. The capture keeps running either way.\n")
print("-" * 60)

seen = set(KNOWN)
fh = open(LOG, encoding="utf-8")
fh.seek(0, os.SEEK_END)          # only new lines from now on

try:
    while True:
        line = fh.readline()
        if not line:
            time.sleep(0.15)
            continue
        m = LINE_RE.match(line.strip())
        if not m:
            continue
        pins = {int(p[1:]) for p in m.group(2).split(",") if p.startswith("D")}
        for pin in sorted(pins - seen):
            seen.add(pin)
            print(f"  {m.group(1)}   NEW PIN: D{pin}  <- this pin reads LOW, "
                  f"so it works")
        # also report a known pin whose first appearance we care about
        for pin in sorted(pins & {p for p in KNOWN if p not in (25, 26, 27, 28, 29)}):
            pass
except KeyboardInterrupt:
    print("\nstopped watching (capture continues)")
finally:
    fh.close()
