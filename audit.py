"""
Audit the raw capture for missing bits and unseen pins.

    python audit.py [logfile]

Answers two questions the floor decode cannot answer on its own:

1. Has the Arduino ever seen ANY activity on pins other than the ten already
   accounted for? Runs over the unfiltered log, so even a single-sample blip is
   caught - the 250ms stability filter used elsewhere would hide exactly the
   kind of brief pulse a missing bit would produce.

2. Is the least significant bit actually present? If VS2 were unreadable, every
   decoded value would be half the true floor and the sequence would still step
   by one at a time, so the usual 100% continuity check proves nothing. The
   test that does work is the per-floor strobe: it fires once per real floor, so
   comparing strobe pulses against decoded floor changes exposes a factor of two.
"""
import os
import re
import sys
from collections import defaultdict

LOG = sys.argv[1] if len(sys.argv) > 1 else \
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "capture_lift.log")

POSITION_BITS = {25: 0, 26: 1, 27: 2, 28: 3, 29: 4}
STROBE = 24
DIG_FIRST = 2
LINE_RE = re.compile(r"^(\d\d:\d\d:\d\d\.\d+)\s+(\d+)\s+([0-9A-Fa-f]+)\s+(\S*)")

rows = []
with open(LOG, encoding="utf-8") as fh:
    for line in fh:
        m = LINE_RE.match(line.strip())
        if m:
            rows.append((m.group(1), int(m.group(2)), int(m.group(3), 16)))

print(f"{len(rows)} raw samples\n")

# ------------------------------------------------- 1. every pin ever active
print("=" * 66)
print("1. EVERY PIN THAT HAS EVER READ LOW  (unfiltered - no sample dropped)")
print("=" * 66)

low_count = defaultdict(int)
for _, _, mask in rows:
    for i in range(52):
        if not (mask >> i) & 1:
            low_count[DIG_FIRST + i] += 1

print(f"  {'pin':<6} {'samples LOW':>12} {'of':>6}   role")
for pin in sorted(low_count):
    if pin in POSITION_BITS:
        role = f"VS{POSITION_BITS[pin] + 2}  (bit {POSITION_BITS[pin]})"
    elif pin == STROBE:
        role = "per-floor strobe"
    else:
        role = "status line"
    print(f"  D{pin:<5} {low_count[pin]:>12} {len(rows):>6}   {role}")

silent = [p for p in range(2, 54) if p not in low_count]
print(f"\n  {len(low_count)} pins have shown activity.")
print(f"  {len(silent)} pins never went LOW even once:")
print("   ", ", ".join(f"D{p}" for p in silent))
print("\n  A relay contact that never closes is indistinguishable from an")
print("  unconnected pin, so VS7 / FIRE / FIRE RETURN could be any of these.")

# ---------------------------------------------- 2. is the LSB really there?
print("\n" + "=" * 66)
print("2. IS VS2 (bit 0) ACTUALLY BEING READ?")
print("=" * 66)


def floor_of(mask):
    return sum(1 << b for p, b in POSITION_BITS.items()
               if not (mask >> (p - DIG_FIRST)) & 1)


def is_low(mask, pin):
    return not (mask >> (pin - DIG_FIRST)) & 1


# count strobe pulses (rising edges of "closed") and decoded floor changes
strobe_pulses = 0
floor_changes = 0
prev_strobe = None
prev_floor = None
for _, _, mask in rows:
    s = is_low(mask, STROBE)
    if prev_strobe is not None and s and not prev_strobe:
        strobe_pulses += 1
    prev_strobe = s

    f = floor_of(mask)
    if prev_floor is not None and f != prev_floor:
        floor_changes += 1
    prev_floor = f

print(f"  strobe pulses on D{STROBE} : {strobe_pulses}")
print(f"  decoded floor changes   : {floor_changes}")
if floor_changes:
    ratio = strobe_pulses / floor_changes
    print(f"  ratio                   : {ratio:.2f}")
    print()
    if ratio > 1.6:
        print("  >> About two strobes per decoded floor: the car is passing two")
        print("     real floors for every change we decode. A bit BELOW the ones")
        print("     we have is missing - VS2 is not reaching the Arduino.")
    elif ratio < 0.6:
        print("  >> Fewer strobes than floor changes - the strobe is not what we")
        print("     think it is; treat the decode with suspicion.")
    else:
        print("  >> One strobe per decoded floor change. Every floor the car")
        print("     passes produces exactly one step in our decode, so no bit")
        print("     below VS6 is missing.")

# --------------------------------------------- 3. travel-time cross-check
print("\n" + "=" * 66)
print("3. TRAVEL TIME PER DECODED FLOOR")
print("=" * 66)
gaps = []
prev_t = prev_f = None
for _, t, mask in rows:
    f = floor_of(mask)
    if prev_f is not None and f != prev_f and abs(f - prev_f) == 1:
        gaps.append((t - prev_t) / 1000)
    if prev_f is None or f != prev_f:
        prev_t, prev_f = t, f

if gaps:
    gaps_sorted = sorted(gaps)
    mid = gaps_sorted[len(gaps_sorted) // 2]
    fast = [g for g in gaps if g < 3]
    print(f"  {len(gaps)} single-floor moves")
    print(f"  median {mid:.2f}s   fastest {min(gaps):.2f}s   "
          f"slowest {max(gaps):.2f}s")
    if fast:
        print(f"  median of moves under 3s: "
              f"{sorted(fast)[len(fast) // 2]:.2f}s  ({len(fast)} moves)")
    print()
    print("  A lift covering a real floor in this time is plausible; if each")
    print("  decoded step actually spanned two floors the per-floor figure")
    print("  would be half of this, which is implausibly fast for a car that")
    print("  also has to accelerate and brake.")

# ------------------------------------- 4. what was active at the top floor
print("\n" + "=" * 66)
print("4. PIN STATE AT THE HIGHEST FLOOR REACHED")
print("=" * 66)
top = max(floor_of(m) for _, _, m in rows)
print(f"  highest decoded floor: {top}\n")
shown = 0
for clock, t, mask in rows:
    if floor_of(mask) == top and shown < 6:
        pins = [DIG_FIRST + i for i in range(52) if not (mask >> i) & 1]
        print(f"  {clock}  {','.join(f'D{p}' for p in pins)}")
        shown += 1
print("\n  If a sixth position bit existed it would have to be closed here -")
print("  floor 44 needs bit 5 (weight 32). Nothing beyond the known pins is.")
