"""capture_status.py verdicts, including the ones --follow introduces."""
import tempfile
import os
import sys

# repo root, not this file's directory
sys.path[0] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
from datetime import datetime, timedelta

import capture_status as cs

os.chdir(tempfile.mkdtemp())


def write(lift, *, start="2026-09-12 10:00:00", port="COM7", beacon=1,
          last_age=5, stopped=False, restarts=0, linklost=0,
          rebind_to=None, wrong_board=None, searching=False):
    def t(age):
        return (datetime.now() - timedelta(seconds=age)).strftime("%H:%M:%S")
    L = ["# lift: %d" % lift, "",
         "===== capture started %s  lift=%d  port=%s =====" % (start, lift, port),
         "--- listening (one-way) 10:00:05 ---"]
    if beacon is not None:
        L.append("--- FW IODebug 1.2.2 2026-08-31 LIFT=%d 10:00:35 ---" % beacon)
    for i in range(restarts):
        L.append("--- board restarted (clock went backwards: 999 -> 89) 10:0%d:00 ---" % i)
    for i in range(linklost):
        L.append("--- link lost 10:0%d:10: GetOverlappedResult failed ---" % i)
    L.append("%s.001    123456  FFFFFFF7F7FFF  D17,D25" % t(last_age + 1))
    if wrong_board:
        L.append("--- wrong board on %s: it says Lift %s, this capture is "
                 "Lift %d %s ---" % (port, wrong_board, lift, t(last_age)))
    if searching:
        L.append("--- searching for Lift %d: COM7=claimed COM9=silent %s ---"
                 % (lift, t(last_age)))
    if rebind_to:
        L.append("--- rebound to %s (was %s) %s ---" % (rebind_to, port, t(last_age)))
        L.append("--- FW IODebug 1.2.2 2026-08-31 LIFT=%d %s ---" % (lift, t(last_age)))
        L.append("%s.001    123999  FFFFFFF7F7FFF  D17,D25" % t(last_age))
    if stopped:
        L.append("===== capture stopped 2026-09-12 11:00:00, 1 changes in "
                 "60.0 min, 0 rejected =====")
    open("capture_lift_%d.log" % lift, "w", encoding="utf-8").write("\n".join(L) + "\n")


HERE = {"1": {"pid": 11, "port": "COM7"}}
MOVED = {"1": {"pid": 11, "port": "COM9"}}

CASES = [
    ("healthy",                       dict(), HERE, "CAPTURING"),
    ("no process",                    dict(), {}, "STOPPED"),
    ("stale, alive",                  dict(last_age=600), HERE, "STALE"),
    ("foreign board id in beacon",    dict(beacon=9), HERE, "DEGRADED"),
    ("no beacon at all",              dict(beacon=None), HERE, "DEGRADED"),
    ("port disagrees with header",    dict(), MOVED, "DEGRADED"),
    ("stopped yet alive",             dict(stopped=True), HERE, "DEGRADED"),
    ("restarts recorded",             dict(restarts=2, linklost=1), HERE, "CAPTURING"),
    # --- what --follow adds ---------------------------------------------
    ("followed its board to COM9",    dict(rebind_to="COM9"), MOVED, "CAPTURING"),
    ("followed, but process on the old port",
                                      dict(rebind_to="COM9"), HERE, "DEGRADED"),
    ("mid-search, quiet for minutes", dict(searching=True, last_age=400),
                                      HERE, "SEARCHING"),
    ("saw a foreign board, then followed",
                                      dict(wrong_board="2", rebind_to="COM9"),
                                      MOVED, "CAPTURING"),
]

fails = 0
for name, kw, procs, want in CASES:
    write(1, **kw)
    got, notes = cs.check(1, procs)
    ok = got == want
    fails += 0 if ok else 1
    print("%-4s %-38s want %-10s got %-10s" % ("ok" if ok else "FAIL", name,
                                               want, got))
    if not ok:
        for n in notes:
            print("        " + n)

# the rebind must be visible in the report, not just silently accepted
write(1, rebind_to="COM9", wrong_board="2")
_, notes = cs.check(1, MOVED)
joined = " | ".join(notes)
for must in ("followed its board 1 time", "rebound to COM9", "foreign board"):
    ok = must in joined
    fails += 0 if ok else 1
    print("%-4s report mentions %r" % ("ok" if ok else "FAIL", must))

print("\n%d failure(s)" % fails)
sys.exit(1 if fails else 0)
