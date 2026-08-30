"""
Score the blind test: decode both lifts and compare with the operator's notes.

    python reveal.py

Also settles lift B's odd inference. On lift A the LSB lives on D24; on lift B
D24 never toggled once, and the subset search patched the hole by drafting D17
(the safety line on A) as bit 4, scoring only 96%. Before decoding B, competing
hypotheses about its wiring are scored explicitly:

    H1  same wiring as A            {24:0, 25:1, 26:2, 27:3, 28:4, 29:5}
    H2  VS2 line dead -> value>>1   {25:0, 26:1, 27:2, 28:3, 29:4}
    H3  the searcher's guess        {25:0, 26:1, 27:2, 28:3, 17:4, 29:5}

judged on single-step continuity, absence of impossible floor 0, and agreement
with the operator's known events.
"""
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
LOG_A = os.path.join(HERE, "capture_lift_3.log")
LOG_B = os.path.join(HERE, "capture_lift_1.log")
MIN_MS = 250
LINE_RE = re.compile(r"^(\d\d:\d\d:\d\d\.\d+)\s+(\d+)\s+([0-9A-Fa-f]+)\s+(\S*)")

BITS_A = {24: 0, 25: 1, 26: 2, 27: 3, 28: 4, 29: 5}

# The operator's answer key. Times are local wall clock, HH:MM.
KEY = [
    ("B", "15:51", 44, "B at top"),
    ("B", "15:52", None, "B sent down to 1"),
    ("A", "15:53", 44, "A at top, then sent down"),
    ("A", "15:55", 44, "A at top again"),
    ("A", "15:56", 1, "A reached bottom"),
    ("A", "16:03", 1, "both parked at 1"),
    ("B", "16:03", 1, "both parked at 1"),
    ("A", "16:15", 9, "called 1 -> 9, then on to 20"),
    ("A", "16:16", 33, "up to 33"),
    ("A", "16:17", 32, "called to 32"),
    ("A", "16:18", 1, "down to 1"),
    ("A", "16:19", 33, "up to wait at 33"),
    ("B", "16:20", 1, "B called from 1"),
    ("B", "16:21", 44, "B at top"),
    ("B", "16:22", None, "B sent down to 1"),
    ("A", "16:24", "B1", "A called to B1"),
    ("A", "16:25", 37, "A parked at 37 until 16:32"),
    ("A", "16:32", 36, "called to 36, then down to 1"),
    ("A", "16:33", 26, "up to 26"),
    ("A", "16:34", 1, "down to 1"),
]


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
    return stable


def decode(pins, bits):
    return sum(1 << i for p, i in bits.items() if p in pins)


def continuity(stable, bits):
    seq = [decode(p, bits) for _, _, p in stable]
    ch = [(a, b) for a, b in zip(seq, seq[1:]) if a != b]
    ok = sum(1 for a, b in ch if abs(b - a) == 1)
    zeros = sum(1 for f in seq if f == 0)
    return (100 * ok / len(ch) if ch else 0), zeros, max(seq) if seq else 0


def clock_to_dt(s):
    return datetime.strptime(s, "%H:%M:%S.%f")


def floor_at(stable, bits, hhmm, spread_s=90):
    """The floor codes present within +/-spread of the given minute."""
    want = datetime.strptime(hhmm, "%H:%M")
    lo, hi = want - timedelta(seconds=spread_s), \
        want + timedelta(seconds=60 + spread_s)
    seen = []
    for clock, _, pins in stable:
        t = clock_to_dt(clock)
        if lo <= t <= hi:
            f = decode(pins, bits)
            if not seen or seen[-1] != f:
                seen.append(f)
    return seen


A = load(LOG_A)
B = load(LOG_B)

# ------------------------------------------------ lift B wiring hypotheses
print("=" * 70)
print("LIFT B WIRING - hypothesis scores")
print("=" * 70)
H = {
    "H1 same-as-A": {24: 0, 25: 1, 26: 2, 27: 3, 28: 4, 29: 5},
    "H2 VS2-dead (>>1)": {25: 0, 26: 1, 27: 2, 28: 3, 29: 4},
    "H3 searcher-guess": {25: 0, 26: 1, 27: 2, 28: 3, 17: 4, 29: 5},
}
print(f"  {'hypothesis':<20} {'single-step':>11} {'floor-0 hits':>13} {'top':>5}")
for name, bits in H.items():
    step, zeros, top = continuity(B, bits)
    print(f"  {name:<20} {step:>10.0f}% {zeros:>13} {top:>5}")

d24_ever = sum(1 for _, _, p in B if 24 in p)
print(f"\n  D24 low on lift B in {d24_ever} of {len(B)} stable states")

# ------------------------------------------------------- answer-key check
print("\n" + "=" * 70)
print("ANSWER KEY vs DECODED DATA")
print("=" * 70)
print(f"  {'lift':<5} {'time':<7} {'operator says':<22} {'codes seen then'}")
print("-" * 70)
for lift, hhmm, label, note in KEY:
    stable = A if lift == "A" else B
    bits = BITS_A if lift == "A" else H["H2 VS2-dead (>>1)"]
    seen = floor_at(stable, bits, hhmm)
    shown = " ".join(str(f) for f in seen[:14]) or "-"
    lab = str(label) if label is not None else "(moving)"
    print(f"  {lift:<5} {hhmm:<7} {lab:<6} {note:<24.24} {shown}")

# ----------------------------------------------- label<->code calibration
print("\n" + "=" * 70)
print("CODE OBSERVED AT EACH LABELLED FLOOR (lift A, 6-bit decode)")
print("=" * 70)
print("  Uses the dwell nearest each keyed event, so transit codes do not")
print("  pollute the table.")


def dwells(stable, bits, min_s=8.0):
    out = []
    for i, (clock, t, pins) in enumerate(stable):
        end = stable[i + 1][1] if i + 1 < len(stable) else t
        f = decode(pins, bits)
        if out and out[-1][0] == f and t - out[-1][2] < 1500:
            out[-1] = (f, out[-1][1], end, out[-1][3])
        else:
            out.append((f, t, end, clock))
    return [(f, (e - s) / 1000, c) for f, s, e, c in out if (e - s) / 1000 >= min_s]


DW_A = dwells(A, BITS_A)
label_events = [(hhmm, lab) for lift, hhmm, lab, _ in KEY
                if lift == "A" and lab is not None]
mapping = {}
for hhmm, lab in label_events:
    want = datetime.strptime(hhmm, "%H:%M")
    best = None
    for f, dur, clock in DW_A:
        dt = clock_to_dt(clock)
        gap = abs((dt - want).total_seconds())
        if gap < 150 and (best is None or gap < best[1]):
            best = (f, gap, dur, clock)
    if best:
        mapping.setdefault(lab, []).append(best[0])

print(f"\n  {'label':>6} -> {'code(s) seen':<14} {'code - label'}")
for lab in sorted((k for k in mapping if isinstance(k, int)),
                  key=lambda x: x) + [k for k in mapping if not isinstance(k, int)]:
    codes = sorted(set(mapping[lab]))
    if isinstance(lab, int):
        diffs = ",".join(f"+{c - lab}" for c in codes)
    else:
        diffs = "-"
    print(f"  {str(lab):>6} -> {str(codes):<14} {diffs}")
