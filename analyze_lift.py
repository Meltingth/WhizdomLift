"""
Work out the pin-to-signal mapping from a capture log. Read-only: safe to run
while log_lift.py is still recording.

    python analyze_lift.py [logfile] [min_ms]

Method
------
Relay contacts do not all change at the same instant, so every floor change
produces a burst of intermediate readings a millisecond or two apart. Those are
switching artefacts, not floors. Anything that does not hold for `min_ms` is
therefore dropped before the analysis starts.

What is left is the real sequence of floor codes. The position encoder counts in
binary, so its least significant bit flips on every floor, the next on every
second floor, then every fourth: ranking pins by how often they toggle recovers
the bit order without any wiring information.

The ranking is then checked rather than trusted - a correct bit order makes
consecutive floors differ by exactly one. A wrong one produces jumps, and the
score says so.
"""
import os
import re
import sys
from collections import defaultdict

LOG = sys.argv[1] if len(sys.argv) > 1 else \
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "capture_lift.log")
MIN_MS = int(sys.argv[2]) if len(sys.argv) > 2 else 250

LINE_RE = re.compile(r"^(\d\d:\d\d:\d\d\.\d+)\s+(\d+)\s+([0-9A-Fa-f]+)\s+(\S*)")
VS_NAME = ["VS2", "VS3", "VS4", "VS5", "VS6", "VS7"]

# ------------------------------------------------------------------ parse
raw = []
with open(LOG, encoding="utf-8") as fh:
    for line in fh:
        m = LINE_RE.match(line.strip())
        if m:
            pins = frozenset(int(p[1:]) for p in m.group(4).split(",")
                             if p.startswith("D"))
            raw.append((int(m.group(2)), pins, m.group(1)))

if len(raw) < 3:
    print(f"Only {len(raw)} samples in {LOG} - not enough to analyse yet.")
    sys.exit(0)

print(f"{LOG}")
print(f"{len(raw)} raw samples, "
      f"{(raw[-1][0] - raw[0][0]) / 1000:.0f}s of board time\n")

# ------------------------------------------------- drop switching artefacts
stable = []
for i, (t, pins, clock) in enumerate(raw):
    dur = (raw[i + 1][0] - t) if i + 1 < len(raw) else MIN_MS
    if dur >= MIN_MS:
        if not stable or stable[-1][1] != pins:
            stable.append((t, pins, clock))

print(f"{len(stable)} states survive the {MIN_MS}ms hold filter "
      f"({len(raw) - len(stable)} discarded as contact-switching noise)\n")

# ------------------------------------------------------- rank by toggling
toggles = defaultdict(int)
for (_, a, _), (_, b, _) in zip(stable, stable[1:]):
    for pin in a ^ b:
        toggles[pin] += 1

active_time = defaultdict(int)
for i, (t, pins, _) in enumerate(stable):
    dur = (stable[i + 1][0] - t) if i + 1 < len(stable) else 0
    for pin in pins:
        active_time[pin] += dur

print("pin    toggles   time closed")
print("-" * 34)
for pin in sorted(set(toggles) | set(active_time)):
    print(f"D{pin:<5}  {toggles[pin]:5d}    {active_time[pin] / 1000:8.1f}s")

ranked = sorted(toggles.items(), key=lambda kv: -kv[1])


def decode(pins, bits):
    return sum(1 << idx for pin, idx in bits.items() if pin in pins)


def score(bits, states):
    """Fraction of floor changes that move exactly one floor."""
    seq = [decode(p, bits) for _, p, _ in states]
    deltas = [abs(b - a) for a, b in zip(seq, seq[1:]) if a != b]
    if not deltas:
        return 0.0, seq
    return sum(1 for d in deltas if d == 1) / len(deltas), seq


# Search over which pins are bits, not merely how many.
#
# Taking the N most-toggling pins is wrong: a strobe that pulses once per floor
# toggles twice per floor change, so it outranks the true least significant bit
# and poisons every candidate that includes it. Only by trying subsets can such
# a pin be left out.
#
# Within a subset the bit order still follows toggle count - a binary counter
# halves its toggle rate at every bit - and the result is scored on whether the
# floors it produces move one step at a time.
from itertools import combinations

# Every pin that moved at all is a candidate. Trimming the pool by toggle rank
# is unsafe: the most significant bit toggles least of all - once per 32 floors -
# so it sits at the bottom of the ranking and a truncated pool drops it,
# silently removing the only correct answer from the search.
pool = [pin for pin, _ in ranked if toggles[pin] >= 1][:12]

# An all-open code is not a floor - the diagram's table starts at 1 - and six
# bits cap the code at 63. A mapping that parks the lift on "floor 0" has the
# bits wrong, so validity is checked before step-continuity.
def validity(seq):
    return sum(1 for f in seq if 1 <= f <= 63) / len(seq) if seq else 0.0

best = None
for n in range(3, min(6, len(pool)) + 1):
    for subset in combinations(pool, n):
        ordered = sorted(subset, key=lambda p: -toggles[p])
        cand = {pin: i for i, pin in enumerate(ordered)}
        s, seq = score(cand, stable)
        key = (round(validity(seq), 4), round(s, 4), n)
        if best is None or key > best[0]:
            best = (key, s, cand, seq, n)

_, s, bits, seq, n = best
excluded = [p for p in pool if p not in bits and toggles[p] > max(
    (toggles[b] for b in bits), default=0) / 2]
print(f"\n{'=' * 58}")
print(f"POSITION BITS - {n} bits, single-step score {s * 100:.0f}%")
print(f"{'=' * 58}")
for pin, idx in sorted(bits.items(), key=lambda kv: kv[1]):
    print(f"  D{pin:<4} -> bit {idx}  {VS_NAME[idx]:<4} weight {1 << idx:>2}"
          f"   ({toggles[pin]} toggles)")

floors = sorted(set(seq))
print(f"\n  floors seen: {floors[0]} .. {floors[-1]}   ({len(floors)} distinct)")
if s >= 0.99:
    print("  -> bit order confirmed: every floor change is a single step")
elif s > 0.7:
    print("  -> mostly consistent, but some changes jump more than one floor")
else:
    print("  -> NOT confirmed; capture more travel before trusting this")

if excluded:
    print(f"\n  excluded from the code: "
          f"{', '.join(f'D{p}' for p in excluded)}")
    print("  toggles faster than the least significant bit, so it pulses per")
    print("  floor rather than carrying a bit - a strobe or 'arrived' signal.")

missing = [VS_NAME[i] for i in range(6) if i not in bits.values()]
if missing:
    need = {4: 16, 5: 32}
    hint = ", ".join(f"{m} needs travel above floor {need.get(VS_NAME.index(m), 0) - 1}"
                     for m in missing)
    print(f"\n  not yet seen: {', '.join(missing)}  ({hint})")

others = [p for p, _ in ranked if p not in bits]
if others:
    print(f"\n{'=' * 58}")
    print("STATUS CANDIDATES (everything that is not a position bit)")
    print(f"{'=' * 58}")
    total = (stable[-1][0] - stable[0][0]) / 1000 or 1
    for pin in others:
        pct = 100 * active_time[pin] / 1000 / total
        print(f"  D{pin:<4} closed {pct:5.1f}% of the time, "
              f"{toggles[pin]} changes")

print(f"\nPOSITION_BITS = {bits}")

# ---------------------------------------------------------- floor timeline
print(f"\n{'=' * 58}")
print("FLOOR TIMELINE")
print(f"{'=' * 58}")
prev = None
for (t, pins, clock), f in zip(stable, seq):
    if f == prev:
        continue
    arrow = "" if prev is None else ("  UP" if f > prev else "  DOWN")
    extra = ",".join(f"D{p}" for p in sorted(pins & set(others)))
    print(f"  {clock}   floor {f:>3}{arrow:<7} {extra}")
    prev = f
