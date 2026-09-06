"""Watch one signal line while somebody works on its wiring.

    python pin_watch.py 1 D24              follow live while repairing
    python pin_watch.py 1 D24 --replay     judge what is already recorded

Reads the capture log that log_lift.py is already writing, NOT the serial
port - Windows opens a COM port exclusively, so the running logger owns it.
Start the capture first; this follows it.

The verdict is what lesson 6.9 exists for: a line that merely goes LOW is not
a working line. A relay contact needs 5-10ms just to close, so closures that
never outlast 50ms are an open-ended wire picking up mains hum. And a position
bit has to MOVE with the car - VS2 is the least significant bit, so it toggles
about once per floor change.
"""
import os
import re
import sys
import time

from lift_decode import lift_id, lift_label, lift_log

HOLD_OK_MS = 50
WINDOW_MS = 90_000            # judge recent behaviour, not the whole history
LINE = re.compile(r"^\d\d:\d\d:\d\d\.\d\d\d\s+(\d+)\s+([0-9A-Fa-f]{13})\s")


def closed(mask, pin):
    return not (mask >> (pin - 2)) & 1


def judge(rows, pin):
    """rows: [(board_ms, mask)] already trimmed to the window."""
    if len(rows) < 3:
        return None, f"{len(rows)} samples - not enough yet"

    upper = [p for p in (25, 26, 27, 28, 29) if p != pin]
    widths, start, toggles = [], None, 0
    for (ms, m), (ms2, m2) in zip(rows, rows[1:]):
        if closed(m, pin) and start is None:
            start = ms
        if closed(m, pin) != closed(m2, pin):
            toggles += 1
            if start is not None and not closed(m2, pin):
                widths.append(ms2 - start)
                start = None
    low = sum(1 for _, m in rows if closed(m, pin))
    seq = [sum(closed(m, p) << i for i, p in enumerate(upper)) for _, m in rows]
    moves = sum(1 for a, b in zip(seq, seq[1:]) if a != b)
    p99 = 0
    if widths:
        widths.sort()
        p99 = widths[min(len(widths) - 1, int(0.99 * len(widths)))]

    # A parked car exercises nothing. VS2 reads HIGH at rest even when it is
    # perfectly healthy, so with no floor movement there is no evidence either
    # way - saying DEAD here would fail a good line for standing still.
    if moves == 0:
        return None, (f"{len(rows):4d} samples | LOW {low:4d} | car has not "
                      f"moved - cannot judge this line yet")

    if low == 0:
        v = "DEAD (open)     - never closes while the car moves"
    elif toggles == 0:
        v = "STUCK           - closed, but never moves"
    elif p99 < HOLD_OK_MS:
        v = f"NOISE           - p99 hold {p99}ms, mains pickup not signal"
    elif moves and not 0.5 <= toggles / moves <= 3.0:
        v = f"SUSPECT         - {toggles/moves:.1f} toggles per floor change"
    else:
        v = "*** WORKING *** - holds and moves with the car"
    return v, (f"{len(rows):4d} samples | LOW {low:4d} | toggles {toggles:4d} "
               f"| p99 hold {p99:6d}ms | floor moves {moves:3d}")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) < 2:
        sys.exit(__doc__)
    replay = "--replay" in sys.argv
    lift = lift_id(args[0])
    pin = int(args[1].lstrip("Dd"))
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        lift_log(lift))
    if not os.path.exists(path):
        sys.exit(f"no capture at {os.path.basename(path)} - "
                 f"start log_lift.py first")

    print(f"D{pin} on {lift_label(lift)} via {os.path.basename(path)}"
          f"{' (replay)' if replay else ''}")

    if replay:
        rows = []
        for line in open(path, encoding="utf-8", errors="replace"):
            m = LINE.match(line.strip())
            if m:
                rows.append((int(m.group(1)), int(m.group(2), 16)))
        if rows:                      # last window of board time
            rows = [r for r in rows if rows[-1][0] - r[0] <= WINDOW_MS]
        v, stats = judge(rows, pin)
        print(f"  {stats}")
        print(f"  {v if v else ''}")
        return

    print("following live - Ctrl-C to stop\n")
    fh = open(path, encoding="utf-8", errors="replace")
    fh.seek(0, os.SEEK_END)
    rows, last = [], 0.0
    try:
        while True:
            line = fh.readline()
            if not line:
                time.sleep(0.2)
            else:
                m = LINE.match(line.strip())
                if m:
                    rows.append((int(m.group(1)), int(m.group(2), 16)))
                    if rows:
                        rows = [r for r in rows
                                if rows[-1][0] - r[0] <= WINDOW_MS]
            if time.time() - last < 3.0:
                continue
            last = time.time()
            v, stats = judge(rows, pin)
            print(f"\r  {stats} | {v}   " if v else f"\r  {stats}   ",
                  end="", flush=True)
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
