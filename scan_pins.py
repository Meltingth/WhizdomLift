"""Find which Arduino pins are really wired to something - read-only.

    python scan_pins.py [runs]

Runs the sketch's 'p' characterisation several times and keeps only the pins
that come back LOW on EVERY run. A genuine wire (a relay input, a closed
contact, a sensor pulling down) is there every single time. A floating pin
drifts, so it appears in some runs and not others - and gets rejected.

That reproducibility check is the whole point: a single scan cannot tell a real
connection from a floating pin picking up interference.

No pin is ever driven, so nothing can be actuated by running this.
"""
import re
import sys
import time

import serial

PORT = "COM3"
BAUD = 115200

# Passes close together are NOT a real test: a floating pin holds its residual
# charge for a few seconds, so back-to-back passes agree with each other and
# look convincingly stable. Spacing them out is what exposes the drift.
RUNS = int(sys.argv[1]) if len(sys.argv) > 1 else 5
GAP = float(sys.argv[2]) if len(sys.argv) > 2 else 4.0

# Must match only the WIRED verdict. The sketch also prints a "LOW ... flickers
# ... noise" line for pins that merely pick up mains hum, and counting those as
# connections is exactly the mistake this tool exists to prevent.
PIN_RE = re.compile(rb"\s+D(\d+)\s+LOW\s+held\s+WIRED")


def collect(ser, timeout=6.0):
    """Send 'p' and gather the pin numbers it reports as LOW."""
    ser.reset_input_buffer()
    ser.write(b"p")
    ser.flush()
    buf = b""
    end = time.time() + timeout
    while time.time() < end:
        buf += ser.read(1024)
        if b"pins have something attached" in buf:
            break
    return set(int(m) for m in PIN_RE.findall(buf)), buf


print(f"Scanning {PORT} - {RUNS} passes, keeping only pins present in all of them.\n")

ser = serial.Serial(PORT, BAUD, timeout=0.3)
ser.dtr = False
ser.rts = False
time.sleep(0.3)
ser.reset_input_buffer()
time.sleep(1.5)                      # let any reset settle

runs = []
for i in range(RUNS):
    pins, _ = collect(ser)
    runs.append(pins)
    shown = ", ".join(f"D{p}" for p in sorted(pins)) if pins else "(none)"
    print(f"  pass {i + 1}: {shown}")
    if i < RUNS - 1:
        time.sleep(GAP)

ser.close()

stable = set.intersection(*runs) if runs else set()
seen = set.union(*runs) if runs else set()

print("\n" + "=" * 58)
print(f"  pin    passes LOW   reading")
for p in sorted(seen):
    hits = sum(1 for r in runs if p in r)
    if hits == RUNS:
        verdict = "WIRED - held low every single pass"
    elif hits > RUNS / 2:
        verdict = "inconsistent - floating, not a connection"
    else:
        verdict = "noise"
    print(f"  D{p:<5}   {hits}/{RUNS}          {verdict}")
print("=" * 58)

if stable:
    print("\nWIRED PINS: " + ", ".join(f"D{p}" for p in sorted(stable)))
    print("These sink current on every pass - something real is attached.")
else:
    print("\nNO PIN IS WIRED.")
    print("Not one pin stayed low across all passes. Every reading drifted,")
    print("which is exactly how an unconnected board behaves: floating pins")
    print("hold residual charge for a few seconds, then wander.")
    print("\nCheck that the Mega is seated in the DNMEGA1 carrier and that the")
    print("relay modules have their 24V supply on.")
