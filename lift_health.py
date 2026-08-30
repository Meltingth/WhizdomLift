"""
Health-check one lift's capture against the known-good reference wiring.

    python lift_health.py 2                 checks capture_lift_2.log
    python lift_health.py 2 --md            also print a markdown block for the report

Lift 3 (labelled A during testing) is the reference: its ten lines were verified against 14 operator-timed
events, so any other lift is judged by how far it deviates from that, rather
than by re-deriving everything from scratch and hoping the answer is sane.

Three questions, in order:

  1. Which of the ten expected lines has this lift ever asserted? A relay
     contact that never closes is electrically identical to a disconnected
     pin, so a line that stays open is either faulty or was never exercised -
     the coverage check below separates those two.

  2. Does the position code decode cleanly with the reference bit map? If it
     does, the wiring matches lift A. If it does not, the alternative maps are
     scored to name the specific line at fault instead of just reporting a
     mismatch.

  3. Do the status lines behave the way lift A's do - UP and DN mutually
     exclusive, RUNNING closed only while moving, SAFETY closed at rest?

Read-only. Safe to run while a capture is still recording.
"""
import os
import re
import sys
from collections import defaultdict
from itertools import combinations

from lift_decode import debounce_pins, lift_id, lift_label, lift_log

HERE = os.path.dirname(os.path.abspath(__file__))
MIN_MS = 250
LINE_RE = re.compile(r"^(\d\d:\d\d:\d\d\.\d+)\s+(\d+)\s+([0-9A-Fa-f]+)\s+(\S*)")

# Verified on lift A. bit 0 is VS2, the least significant.
REF_BITS = {24: 0, 25: 1, 26: 2, 27: 3, 28: 4, 29: 5}
REF_STATUS = {16: "RUNNING", 17: "SAFETY", 19: "UP", 20: "DN"}
VS = ["VS2", "VS3", "VS4", "VS5", "VS6", "VS7"]

# Lines that only close in an alarm condition; absence is expected, not a fault.
ALARM_ONLY = "FIRE / FIRE RETURN"


def load(lift):
    path = os.path.join(HERE, lift_log(lift))
    if not os.path.exists(path):
        raise SystemExit(
            f"no capture found: {os.path.basename(path)}\n"
            f"  start one with:  python log_lift.py <PORT> {lift_id(lift)}")
    rows = []
    # Where one capture session ends and the next begins. Nothing was recorded
    # across that gap, so the last state before it must not be credited with
    # the time it spans - we simply were not looking. This is not the same as
    # a board reset: the board keeps running, its clock does not go backwards,
    # and nothing in the data itself gives the gap away.
    session_starts = set()
    fresh = False
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line.startswith("===== capture started"):
                fresh = True
                continue
            m = LINE_RE.match(line)
            if m:
                pins = frozenset(int(p[1:]) for p in m.group(4).split(",")
                                 if p.startswith("D"))
                row = (m.group(1), int(m.group(2)), pins)
                if fresh:
                    session_starts.add(row[:2])
                    fresh = False
                rows.append(row)
    # Settle each line on its own. A single chattering contact would otherwise
    # make every combined state too short-lived to survive a whole-state filter.
    stable = debounce_pins(rows, hold_ms=MIN_MS)
    return path, rows, stable, session_starts


def pulse_widths(rows):
    """For each pin, how long it stayed closed on each occasion, in ms."""
    segs = [[]]
    for r in rows:
        if segs[-1] and r[1] < segs[-1][-1][1]:      # board reset between runs
            segs.append([])
        segs[-1].append(r)
    out = {}
    for pin in list(REF_BITS) + list(REF_STATUS):
        w = []
        for seg in segs:
            prev = start = None
            for _, t, low in seg:
                cur = pin in low
                if prev is None:
                    prev, start = cur, t
                    continue
                if cur != prev:
                    if prev:
                        w.append(t - start)
                    prev, start = cur, t
        out[pin] = w
    return out


def decode(pins, bits):
    return sum(1 << i for p, i in bits.items() if p in pins)


def score(stable, bits):
    seq = [decode(p, bits) for _, _, p in stable]
    ch = [(a, b) for a, b in zip(seq, seq[1:]) if a != b]
    if not ch:
        return 0.0, seq
    return sum(1 for a, b in ch if abs(b - a) == 1) / len(ch), seq


def main():
    lift = lift_id(sys.argv[1] if len(sys.argv) > 1 else "3")
    want_md = "--md" in sys.argv
    path, rows, stable, session_starts = load(lift)

    print("=" * 68)
    print(f"{lift_label(lift)} — HEALTH CHECK vs Lift 3 reference wiring")
    print("=" * 68)
    print(f"  {os.path.basename(path)}: {len(rows)} raw samples, "
          f"{len(stable)} stable states")
    if len(stable) < 20:
        print("\n  NOT ENOUGH DATA. Run the car through a full trip "
              "(bottom to top and back)\n  before trusting anything below.")
        if len(stable) < 4:
            return

    # ---------------------------------------------------- 1. line presence
    low_count = defaultdict(int)
    for _, _, pins in rows:
        for p in pins:
            low_count[p] += 1

    toggles = defaultdict(int)
    for (_, _, a), (_, _, b) in zip(stable, stable[1:]):
        for p in a ^ b:
            toggles[p] += 1

    print("\n" + "-" * 68)
    print("1. EXPECTED LINES")
    print("-" * 68)
    # How long does each line actually hold once closed? A line that only ever
    # closes for a couple of milliseconds is not a relay contact - a mechanical
    # relay needs 5-10ms merely to close - so counting raw LOW samples and
    # calling it "ok" hides a line that carries nothing but induced noise.
    widths = pulse_widths(rows)

    def classify(pin):
        """Judge a line on its 99th percentile closure, not its longest.

        Using the maximum makes the verdict hinge on a single sample: Lift 2's
        SAFETY line logged one 304ms closure among 79,664, every other one of
        them 2-4ms, and that lone outlier was enough to relabel a dead line as
        healthy. A high percentile ignores the stray while still reacting the
        moment a line genuinely starts holding.
        """
        seen = low_count.get(pin, 0)
        if seen == 0:
            return "MISSING", None, 0
        w = sorted(widths.get(pin) or [])
        if not w:
            # Closed for the entire capture, so no closure ever completed and
            # there is nothing to measure. That is exactly how a
            # normally-closed line such as SAFETY should behave - counting it
            # as missing inverts the verdict on the healthiest signal there is.
            frac = seen / max(len(rows), 1)
            if frac > 0.9:
                return "HELD", None, 0
            return "MISSING", None, 0
        p99 = w[min(len(w) - 1, int(len(w) * 0.99))]
        long_ones = sum(1 for x in w if x >= 50)
        if p99 < 50:
            return "NOISE", p99, long_ones
        return "ok", w[-1], long_ones

    print(f"  {'pin':<5} {'expected':<12} {'closings':>9} {'p99 hold':>9}   status")
    missing_bits, missing_status = [], []
    noisy = []
    for pin, bit in sorted(REF_BITS.items(), key=lambda kv: kv[1]):
        mark, longest, long_ones = classify(pin)
        if mark == "MISSING":
            missing_bits.append((pin, bit))
        elif mark == "NOISE":
            noisy.append((pin, VS[bit], longest, long_ones))
        shown = f"{longest}ms" if longest is not None else (
            "whole run" if mark == "HELD" else "-")
        print(f"  D{pin:<4} {VS[bit] + ' bit' + str(bit):<12} "
              f"{len(widths.get(pin) or []):>9} {shown:>9}   {mark}")
    for pin, name in sorted(REF_STATUS.items()):
        mark, longest, long_ones = classify(pin)
        if mark == "MISSING":
            missing_status.append((pin, name))
        elif mark == "NOISE":
            noisy.append((pin, name, longest, long_ones))
        shown = f"{longest}ms" if longest is not None else (
            "whole run" if mark == "HELD" else "-")
        print(f"  D{pin:<4} {name:<12} {len(widths.get(pin) or []):>9} "
              f"{shown:>9}   {mark}")

    if noisy:
        print(f"\n  NOISE = the line closes, but never for longer than 50ms.")
        print(f"  A relay contact cannot behave that way; this is an open-ended")
        print(f"  wire picking up mains hum, so the signal is not arriving.")

    extra = sorted(p for p in low_count if p not in REF_BITS and p not in REF_STATUS)
    if extra:
        print(f"\n  unexpected active pins: "
              f"{', '.join('D%d' % p for p in extra)}")
        print(f"  (could be {ALARM_ONLY}, or wiring that differs from lift A)")

    # ------------------------------------------------- 2. decode with ref map
    print("\n" + "-" * 68)
    print("2. POSITION DECODE")
    print("-" * 68)
    ref_step, ref_seq = score(stable, REF_BITS)
    ref_max = max(ref_seq) if ref_seq else 0
    ref_zero = sum(1 for f in ref_seq if f == 0)
    print(f"  reference map    single-step {ref_step * 100:5.0f}%   "
          f"top code {ref_max:>3}   floor-0 readings {ref_zero}")

    verdict_bits = None
    if ref_step >= 0.99 and ref_zero == 0:
        print("  -> wiring matches lift A exactly.")
        verdict_bits = "OK"
    else:
        # Re-derive from the lines that actually moved. A dead line makes the
        # reference map produce jumps; whichever subset steps cleanly names the
        # real layout, and the gap between the two names the faulty wire.
        pool = [p for p, n in sorted(toggles.items(), key=lambda kv: -kv[1])
                if n >= 1][:12]
        best = None
        for n in range(3, min(6, len(pool)) + 1):
            for subset in combinations(pool, n):
                ordered = sorted(subset, key=lambda p: -toggles[p])
                cand = {p: i for i, p in enumerate(ordered)}
                s, seq = score(stable, cand)
                zeros = sum(1 for f in seq if f == 0)
                key = (round(s, 4), -zeros, n)
                if best is None or key > best[0]:
                    best = (key, cand, s, seq)
        if best:
            _, cand, s, seq = best
            print(f"  best-fit map     single-step {s * 100:5.0f}%   "
                  f"top code {max(seq):>3}")
            print("    " + ", ".join(f"D{p}=bit{i}" for p, i in
                                     sorted(cand.items(), key=lambda kv: kv[1])))
            shifted = [(p, REF_BITS[p], cand[p]) for p in cand
                       if p in REF_BITS and cand[p] != REF_BITS[p]]
            if missing_bits and shifted:
                pin, bit = missing_bits[0]
                print(f"\n  -> D{pin} ({VS[bit]}) carries no signal, and every line "
                      f"above it\n     reads one bit position low as a result. "
                      f"Position resolution is\n     coarse by a factor of "
                      f"{2 ** (bit + 1)} until that wire is repaired.")
                verdict_bits = f"FAULT: D{pin} ({VS[bit]}) dead"
            elif shifted:
                print("\n  -> pin-to-bit order differs from lift A "
                      "(wiring order, not a fault)")
                verdict_bits = "different wiring order"
            else:
                verdict_bits = "unclear - capture more travel"

    # ------------------------------------------------------ 3. status lines
    print("\n" + "-" * 68)
    print("3. STATUS LINES")
    print("-" * 68)
    bits_for_move = REF_BITS if ref_step >= 0.99 else (best[1] if best else REF_BITS)
    kinds = []
    seq = [decode(p, bits_for_move) for _, _, p in stable]
    # Board time restarts at 0 on every reboot and this log accumulates many
    # sessions, so differencing straight across that seam gives a large
    # negative hold. pulse_widths() above already splits on it; this did not,
    # and the negatives then dragged the per-pin totals below zero - which is
    # what the impossible negative percentages in section 3 were. A sample
    # sitting on a seam has no measurable hold, so give it none.
    hold = []
    for i in range(len(stable)):
        if i + 1 >= len(stable):
            hold.append(0.0)
            continue
        # A sample sitting on a recording gap has no measurable hold either:
        # the state may have changed the moment we stopped listening.
        if stable[i + 1][:2] in session_starts:
            hold.append(0.0)
            continue
        d = (stable[i + 1][1] - stable[i][1]) / 1000
        hold.append(d if d >= 0 else 0.0)
    for i, f in enumerate(seq):
        if hold[i] >= 3.0:
            kinds.append("idle")
        elif i + 1 < len(seq):
            kinds.append("up" if seq[i + 1] > f else "down" if seq[i + 1] < f else "idle")
        else:
            kinds.append("idle")

    tot = defaultdict(float)
    per = defaultdict(lambda: defaultdict(float))
    for i in range(len(stable)):
        tot[kinds[i]] += hold[i]
        for p in stable[i][2]:
            per[p][kinds[i]] += hold[i]

    print(f"  {'pin':<5} {'expected':<9} {'UP':>6} {'DOWN':>6} {'IDLE':>6}   matches lift A?")
    for pin, name in sorted(REF_STATUS.items(), key=lambda kv: kv[1]):
        up = 100 * per[pin]["up"] / tot["up"] if tot["up"] else 0
        dn = 100 * per[pin]["down"] / tot["down"] if tot["down"] else 0
        idle = 100 * per[pin]["idle"] / tot["idle"] if tot["idle"] else 0
        if name == "UP":
            ok = up > 60 and dn < 25
        elif name == "DN":
            ok = dn > 60 and up < 25
        elif name == "RUNNING":
            ok = up > 60 and dn > 60 and idle < 40
        else:  # SAFETY
            ok = idle > 90
        print(f"  D{pin:<4} {name:<9} {up:>5.0f}% {dn:>5.0f}% {idle:>5.0f}%   "
              f"{'yes' if ok else 'NO - check this line'}")

    # ------------------------------------------------------------ coverage
    print("\n" + "-" * 68)
    print("4. COVERAGE")
    print("-" * 68)
    top = max(seq) if seq else 0
    print(f"  codes seen: {min(seq)}..{top}")

    # Judge coverage by whether the top bit's own line ever closed, not by the
    # decoded range. When a low bit is dead the decoded values are halved, so a
    # range-based test would claim the car never went high enough even as the
    # top line was closing perfectly well.
    top_pin = max(REF_BITS, key=lambda p: REF_BITS[p])
    full_range = low_count.get(top_pin, 0) > 0

    def exercised(bit):
        """Did the car travel far enough for this bit to have to close?"""
        return full_range or top >= (1 << bit)

    if full_range:
        print(f"  D{top_pin} ({VS[REF_BITS[top_pin]]}) closed "
              f"{low_count[top_pin]} times, so the car reached the top of the")
        print(f"  encoder range - every position bit had its chance to close.")
    elif top < 32:
        print(f"  D{top_pin} ({VS[REF_BITS[top_pin]]}) never closed, but the top "
              f"code is only {top}.")
        print(f"  That line is only asserted above code 31, so its silence "
              f"proves nothing yet -")
        print(f"  send the car to the top floor before judging it.")
    else:
        print(f"  D{top_pin} ({VS[REF_BITS[top_pin]]}) never closed despite the "
              f"car covering the full range - genuine fault.")
    print(f"  {ALARM_ONLY}: not exercised unless an alarm is triggered.")

    # ------------------------------------------------------------- verdict
    print("\n" + "=" * 68)
    print("VERDICT")
    print("=" * 68)
    faults = []
    for p, b in missing_bits:
        if exercised(b):
            faults.append(f"D{p} ({VS[b]}) sends nothing — FAULT")
        else:
            faults.append(f"D{p} ({VS[b]}) unseen, but the car never went high "
                          f"enough to need it — inconclusive")
    faults += [f"D{p} ({n}) sends nothing" for p, n in missing_status]
    faults += [f"D{p} ({n}) carries only noise - 99% of closures under {w}ms"
               + (f", {c} stray longer one(s)" if c else "")
               for p, n, w, c in noisy]
    if not faults and verdict_bits == "OK":
        print("  HEALTHY - all ten lines present and decoding matches lift A.")
        held = [p for p in list(REF_BITS) + list(REF_STATUS)
                if classify(p)[0] == "HELD"]
        if held:
            print("  " + ", ".join(f"D{p}" for p in sorted(held))
                  + " stayed closed for the whole run, as a normally-closed"
                  " line should.")
    else:
        for f in faults:
            print(f"  - {f}")
        if verdict_bits and verdict_bits != "OK":
            print(f"  - position decode: {verdict_bits}")
        print("\n  To localise a dead line: with the car moving, watch that")
        print("  channel's LED on the relay module.")
        print("    LED blinks but the pin stays open -> relay output to the")
        print("      DNMEGA1 terminal is loose or broken")
        print("    LED does not blink -> controller contact to the module")
        print("      input is the broken leg")

    if want_md:
        print("\n" + "-" * 68)
        print(f"### ลิฟต์ {lift}\n")
        print(f"- ข้อมูล: {len(rows)} raw / {len(stable)} stable, codes {min(seq)}..{top}")
        print(f"- decode ด้วยแผนที่อ้างอิง: single-step {ref_step * 100:.0f}%")
        if faults:
            for f in faults:
                print(f"- ⚠️ {f}")
        else:
            print("- ✅ ครบทั้ง 10 เส้น ตรงกับลิฟต์ A")


if __name__ == "__main__":
    main()
