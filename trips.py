"""
Turn a capture log into trips: where the car went, where it stopped, and which
status line means what. Read-only, safe to run while recording continues.

    python trips.py [logfile]

A stop is a floor held longer than DWELL_S while the car is otherwise making a
journey - that is what distinguishes picking someone up from simply passing by.

The direction lines are then identified by correlation rather than assumption:
whichever pin is closed during upward travel and open during downward travel is
UP, and a pin closed for both is RUNNING. No wiring information is needed.
"""
import os
import re
import sys
from collections import defaultdict

LOG = sys.argv[1] if len(sys.argv) > 1 else \
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "capture_lift_3.log")
MIN_MS = 250        # shorter than this is contact bounce, not a floor
DWELL_S = 3.0       # a floor held this long mid-journey counts as a stop

# Six bits, confirmed on the fast-sampling capture: 729 stable states, 100%
# single-step, top code 46. The earlier 5-bit map was an artefact of the old
# sketch blocking its own sampling loop with serial prints and aliasing D24.
POSITION_BITS = {24: 0, 25: 1, 26: 2, 27: 3, 28: 4, 29: 5}   # VS2..VS7
CANDIDATE_VS7 = []                                     # resolved: VS7 = D29

LINE_RE = re.compile(r"^(\d\d:\d\d:\d\d\.\d+)\s+(\d+)\s+([0-9A-Fa-f]+)\s+(\S*)")

samples = []
with open(LOG, encoding="utf-8") as fh:
    for line in fh:
        m = LINE_RE.match(line.strip())
        if m:
            pins = frozenset(int(p[1:]) for p in m.group(4).split(",")
                             if p.startswith("D"))
            samples.append((int(m.group(2)), pins, m.group(1)))

# collapse switching artefacts
stable = []
for i, (t, pins, clock) in enumerate(samples):
    dur = (samples[i + 1][0] - t) if i + 1 < len(samples) else MIN_MS
    if dur >= MIN_MS and (not stable or stable[-1][1] != pins):
        stable.append((t, pins, clock))


def floor_of(pins, extra_bit=None):
    f = sum(1 << b for p, b in POSITION_BITS.items() if p in pins)
    if extra_bit is not None and extra_bit in pins:
        f += 32
    return f


# ---------------------------------------------------- is one of them VS7?
# VS7 is worth 32, so with it the reachable range doubles. The right pin is the
# one that makes the floor sequence keep stepping by one instead of folding
# back at 31 - a wrong choice produces jumps.
print("Testing which unexplained pin could be VS7 (bit 5, weight 32):\n")
print(f"  {'pin':<6} {'max floor':>9}  {'single-step':>11}")
base_seq = [floor_of(p) for _, p, _ in stable]
base_ok = sum(1 for a, b in zip(base_seq, base_seq[1:]) if a != b and abs(b - a) == 1)
base_n = sum(1 for a, b in zip(base_seq, base_seq[1:]) if a != b)
print(f"  {'none':<6} {max(base_seq):>9}  "
      f"{100 * base_ok / base_n if base_n else 0:>10.0f}%")

for pin in CANDIDATE_VS7:
    seq = [floor_of(p, pin) for _, p, _ in stable]
    changes = [(a, b) for a, b in zip(seq, seq[1:]) if a != b]
    ok = sum(1 for a, b in changes if abs(b - a) == 1)
    print(f"  D{pin:<5} {max(seq):>9}  "
          f"{100 * ok / len(changes) if changes else 0:>10.0f}%")

print("\nA pin that is really VS7 keeps the score at 100% while raising the")
print("ceiling. One that drops the score is a status line, not a bit.\n")

# ------------------------------------------------------------ trips/stops
# Merge consecutive samples that decode to the same floor. Status lines change
# while the car sits still, which creates fresh states at an unchanged floor;
# leaving those in place chops every journey into one-floor fragments.
# Duration of each raw stable sample - needed because the status lines change
# WITHIN a floor, so they must be weighted by their own time on air rather than
# by the floor's. Unioning the pins seen during a floor would mark a line that
# blinked once as closed for the whole stay.
stable_dur = [((stable[k + 1][0] - stable[k][0]) / 1000)
              if k + 1 < len(stable) else 0.0
              for k in range(len(stable))]

merged = []
for idx, (t, pins, clock) in enumerate(stable):
    f = floor_of(pins)
    if merged and merged[-1][1] == f:
        merged[-1][4].append(idx)           # member samples, kept separate
        merged[-1][3] = t
    else:
        merged.append([t, f, clock, t, [idx]])

# close out durations: end of an entry is the start of the next
for k in range(len(merged) - 1):
    merged[k][3] = merged[k + 1][0]
if merged:
    merged[-1][3] = merged[-1][0]

floors = [(m[0], m[1], m[4], m[2]) for m in merged]     # m[4] = member indices
hold_s = [(m[3] - m[0]) / 1000 for m in merged]

print("=" * 66)
print("FLOOR SEQUENCE (merged)")
print("=" * 66)
line = []
for (_, f, _, _), h in zip(floors, hold_s):
    line.append(f"{f}" + (f"[{h:.0f}s]" if h >= DWELL_S else ""))
print("  " + " ".join(line))
print(f"\n  {len(floors)} distinct floor states, "
      f"range {min(f for _, f, _, _ in floors)}..{max(f for _, f, _, _ in floors)}")

print("=" * 66)
print("JOURNEYS AND STOPS")
print("=" * 66)

# Classify every floor state first. A floor held longer than DWELL_S is the car
# standing still, whatever happens either side of it - folding those seconds
# into the adjoining journey is what made a 7-floor hop look like it took five
# and a half minutes, and it swamps the status correlation with idle time.
kind = []
for k, (_, f, _, _) in enumerate(floors):
    if hold_s[k] >= DWELL_S:
        kind.append("idle")
    elif k + 1 < len(floors):
        nxt = floors[k + 1][1]
        kind.append("up" if nxt > f else "down" if nxt < f else "idle")
    else:
        kind.append("idle")

# A journey is a maximal run of same-direction moves; a dwell ends it.
trips = []
i = 0
while i < len(floors) - 1:
    if kind[i] == "idle":
        i += 1
        continue
    d = kind[i]
    j = i
    while j + 1 < len(floors) and kind[j] == d:
        j += 1
    trips.append((i, j, d))
    i = j

for n, (a, b, d) in enumerate(trips, 1):
    f0, f1 = floors[a][1], floors[b][1]
    secs = (floors[b][0] - floors[a][0]) / 1000
    print(f"\ntrip {n}: {d.upper():<4} floor {f0} -> {f1}   "
          f"{floors[a][3]} to {floors[b][3]}   "
          f"({secs:.0f}s, {abs(f1 - f0)} floors, "
          f"{secs / max(abs(f1 - f0), 1):.1f}s per floor)")
    if hold_s[b] >= DWELL_S:
        print(f"    then stood at floor {f1} for {hold_s[b]:.0f}s")

# Intermediate stops: a dwell with travel in the SAME direction on both sides
# is a pick-up en route; a dwell where the direction reverses is a terminus.
print("\n" + "-" * 66)
print("DWELLS  (a stop between two moves in the same direction is a pick-up)")
print("-" * 66)
found = False
for k in range(1, len(floors) - 1):
    if kind[k] != "idle" or hold_s[k] < DWELL_S:
        continue
    # Direction is taken from the floors either side of this one, not from the
    # last time the car was moving. Skipping back over an earlier dwell reports
    # the previous journey's direction, which turns a genuine pick-up on the way
    # up into a bogus "turnaround".
    prev_f, here_f, next_f = floors[k - 1][1], floors[k][1], floors[k + 1][1]
    before = "up" if here_f > prev_f else "down" if here_f < prev_f else None
    after = "up" if next_f > here_f else "down" if next_f < here_f else None
    if before is None or after is None:
        continue
    label = ("PICK-UP en route" if before == after else
             f"turnaround ({before} then {after})")
    print(f"  floor {floors[k][1]:>3}  held {hold_s[k]:6.1f}s  "
          f"{floors[k][3]}   {label}")
    found = True
if not found:
    print("  none")

# ------------------------------------------------- status pin correlation
print("\n" + "=" * 66)
print("STATUS LINES, BY WHAT THE CAR WAS DOING")
print("=" * 66)

buckets = defaultdict(lambda: defaultdict(float))
totals = defaultdict(float)
for k in range(len(floors)):
    for s in floors[k][2]:                  # each raw sample inside this floor
        dur = stable_dur[s]
        totals[kind[k]] += dur
        for pin in stable[s][1]:
            buckets[pin][kind[k]] += dur

print(f"  {'pin':<6} {'UP':>7} {'DOWN':>7} {'STOPPED':>9}   reading")
for pin in sorted(buckets):
    if pin in POSITION_BITS:
        continue
    up = 100 * buckets[pin]["up"] / totals["up"] if totals["up"] else 0
    dn = 100 * buckets[pin]["down"] / totals["down"] if totals["down"] else 0
    idle = 100 * buckets[pin]["idle"] / totals["idle"] if totals["idle"] else 0
    if idle > 90 and up > 90 and dn > 90:
        verdict = "closed always - safety / 安全"
    elif up > 60 and dn < 25:
        verdict = "UP / 上行"
    elif dn > 60 and up < 25:
        verdict = "DN / 下行"
    elif up > 60 and dn > 60 and idle < 40:
        verdict = "RUNNING / 运行"
    else:
        verdict = "unclear - needs more data"
    print(f"  D{pin:<5} {up:>6.0f}% {dn:>6.0f}% {idle:>8.0f}%   {verdict}")
print(f"\n  time budget: up {totals['up']:.0f}s, down {totals['down']:.0f}s, "
      f"stopped {totals['idle']:.0f}s")
