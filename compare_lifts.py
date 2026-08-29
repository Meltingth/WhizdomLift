"""
Compare two lifts' captures side by side.

    python compare_lifts.py [logA] [logB]

Defaults: capture_lift.log (lift A on COM3) vs the newest capture_lift_COM*.log
(lift B). Read-only - run any time, both captures keep recording.

Two independent checks, and it matters not to conflate them:

1. WIRING - for each board separately, infer the position bits from toggle
   behaviour (exactly as was done for lift A) and report both mappings. If the
   two boards are wired the same, the same Arduino pins come out as the same
   bits. Any difference here is physical wiring, nothing to do with the lift.

2. SEMANTICS - decode each board with its OWN inferred bits and compare the
   floor ranges and top-of-travel codes. If both lifts top out at the same code
   for the same labelled floor, that number is what the controllers genuinely
   transmit, and any gap between code and floor label is the building's
   numbering scheme, not a fault. If they top out differently, the lift whose
   code is lower has a genuine upstream problem worth chasing.

Timelines are aligned on wall-clock time, which both loggers stamp from the
same PC clock, so simultaneous events line up regardless of board uptimes.
"""
import glob
import os
import re
import sys
from collections import defaultdict
from itertools import combinations

HERE = os.path.dirname(os.path.abspath(__file__))
MIN_MS = 250

LINE_RE = re.compile(r"^(\d\d:\d\d:\d\d\.\d+)\s+(\d+)\s+([0-9A-Fa-f]+)\s+(\S*)")


def pick_logs():
    a = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "capture_lift.log")
    if len(sys.argv) > 2:
        b = sys.argv[2]
    else:
        others = sorted(glob.glob(os.path.join(HERE, "capture_lift_COM*.log")),
                        key=os.path.getmtime)
        b = others[-1] if others else None
    return a, b


def load(path):
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            m = LINE_RE.match(line.strip())
            if m:
                pins = frozenset(int(p[1:]) for p in m.group(4).split(",")
                                 if p.startswith("D"))
                rows.append((m.group(1), int(m.group(2)), pins))
    stable = []
    for i, (clock, t, pins) in enumerate(rows):
        dur = (rows[i + 1][1] - t) if i + 1 < len(rows) else MIN_MS
        if dur >= MIN_MS and (not stable or stable[-1][2] != pins):
            stable.append((clock, t, pins))
    return rows, stable


def infer_bits(stable):
    """Same subset-search used to crack lift A, packaged for reuse."""
    toggles = defaultdict(int)
    for (_, _, a), (_, _, b) in zip(stable, stable[1:]):
        for pin in a ^ b:
            toggles[pin] += 1
    pool = [p for p, n in sorted(toggles.items(), key=lambda kv: -kv[1])
            if n >= 1][:12]

    def decode(pins, bits):
        return sum(1 << i for p, i in bits.items() if p in pins)

    def run(bits):
        seq = [decode(p, bits) for _, _, p in stable]
        ch = [(x, y) for x, y in zip(seq, seq[1:]) if x != y]
        step = sum(1 for x, y in ch if abs(y - x) == 1) / len(ch) if ch else 0
        valid = sum(1 for f in seq if 1 <= f <= 63) / len(seq) if seq else 0
        return valid, step, seq

    best = None
    for n in range(3, min(6, len(pool)) + 1):
        for subset in combinations(pool, n):
            ordered = sorted(subset, key=lambda p: -toggles[p])
            cand = {p: i for i, p in enumerate(ordered)}
            valid, step, seq = run(cand)
            key = (round(valid, 4), round(step, 4), n)
            if best is None or key > best[0]:
                best = (key, cand, seq, step)
    if best is None:
        return {}, [], 0.0, toggles
    _, bits, seq, step = best
    return bits, seq, step, toggles


def summarise(name, path):
    rows, stable = load(path)
    if len(stable) < 4:
        print(f"  {name}: only {len(stable)} stable states - not enough yet")
        return None
    bits, seq, step, toggles = infer_bits(stable)
    print(f"\n  {name}  ({os.path.basename(path)})")
    print(f"    stable states : {len(stable)}   raw: {len(rows)}")
    print(f"    position bits : " + ", ".join(
        f"D{p}=bit{i}" for p, i in sorted(bits.items(), key=lambda kv: kv[1])))
    print(f"    single-step   : {step * 100:.0f}%")
    if seq:
        print(f"    floor range   : {min(seq)}..{max(seq)}")
    status = [p for p in toggles if p not in bits]
    if status:
        print(f"    other pins    : " + ", ".join(
            f"D{p}({toggles[p]})" for p in sorted(status)))
    return {"bits": bits, "seq": seq, "stable": stable, "step": step}


log_a, log_b = pick_logs()
print("=" * 66)
print("LIFT-TO-LIFT COMPARISON")
print("=" * 66)

A = summarise("lift A", log_a)
if log_b is None or not os.path.exists(log_b or ""):
    print("\n  lift B: no capture_lift_COM*.log found yet.")
    print("  Plug the second board in and start its logger first.")
    sys.exit(0)
B = summarise("lift B", log_b)
if not A or not B:
    sys.exit(0)

print("\n" + "=" * 66)
print("VERDICTS")
print("=" * 66)

pa = {i: p for p, i in A["bits"].items()}
pb = {i: p for p, i in B["bits"].items()}
same_pins = all(pa.get(i) == pb.get(i) for i in set(pa) | set(pb))
if same_pins:
    print("  wiring   : IDENTICAL - same Arduino pin carries the same bit on")
    print("             both boards. Any code difference is controller-side.")
else:
    print("  wiring   : DIFFERENT pin-to-bit layout:")
    for i in sorted(set(pa) | set(pb)):
        print(f"               bit {i}: lift A D{pa.get(i, '?')}  "
              f"lift B D{pb.get(i, '?')}")
    print("             (decoding compensates for this automatically; it only")
    print("              means the physical wiring order differs)")

ta, tb = max(A["seq"]), max(B["seq"])
print(f"\n  top code : lift A = {ta}   lift B = {tb}")
if ta == tb:
    print("             Both controllers top out at the same value. That value")
    print("             is what the system transmits for the top landing - the")
    print("             gap to the floor label is numbering, not a fault.")
else:
    print("             They differ. If both cars really visited the same top")
    print("             landing, the lower one is missing a bit upstream:")
    print("             check that lift's controller-to-relay wiring first.")
