"""Exercise the --follow search on ports that cannot be produced with the
hardware on this machine: a lift that moved, two boards with the same id,
a port held by another capture, boards that never name themselves.

Nothing here opens a serial port -- the probe is injected.
"""
import io
import os
import sys

# repo root, not this file's directory
sys.path[0] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.argv = ["log_lift.py", "COM20", "1", "--listen", "--follow"]
import log_lift as L


class FakeLog(io.StringIO):
    def write(self, s):
        super().write(s)
        return len(s)


def run(world, lift="1"):
    """world: port -> ('identified', lift) | ('claimed', None) | ..."""
    L.candidate_ports = lambda: list(world)
    log = FakeLog()
    try:
        got = L.reacquire(lift, log, probe=lambda p: world[p])
        return got, log.getvalue()
    except SystemExit as e:
        return ("EXIT", str(e)), log.getvalue()


CASES = [
    ("same socket, same number",
     {"COM20": ("identified", "1")}, "COM20"),

    ("dongle moved to another socket",
     {"COM20": ("silent", None), "COM30": ("identified", "1")}, "COM30"),

    ("two dongles swapped -- ours is the one that says 1",
     {"COM20": ("identified", "2"), "COM22": ("identified", "1")}, "COM22"),

    ("our port held by another capture -- skipped, not stolen",
     {"COM20": ("claimed", None), "COM30": ("identified", "1")}, "COM30"),

    ("everything claimed -- wait, never guess",
     {"COM20": ("claimed", None), "COM22": ("claimed", None)}, None),

    ("dongle dead, nothing announces us",
     {"COM20": ("silent", None), "COM22": ("identified", "3")}, None),

    ("board with no LIFT= field is not adoptable",
     {"COM20": ("quiet", None)}, None),

    ("port vanished mid-scan",
     {"COM20": ("gone", None), "COM31": ("identified", "1")}, "COM31"),

    ("driver error on one port does not stop the search",
     {"COM20": ("error", "SetCommState failed"), "COM31": ("identified", "1")},
     "COM31"),

    ("no ports at all",
     {}, None),
]

fails = 0
for name, world, want in CASES:
    got, logged = run(world)
    ok = got == want
    fails += 0 if ok else 1
    print("%-4s %-52s want %-8s got %s" % ("ok" if ok else "FAIL", name,
                                           want, got))

# the one case that must stop the process outright
got, logged = run({"COM20": ("identified", "1"), "COM30": ("identified", "1")})
ok = isinstance(got, tuple) and got[0] == "EXIT" and "same -DLIFT_ID" in got[1]
fails += 0 if ok else 1
print("%-4s %-52s want %-8s got %s"
      % ("ok" if ok else "FAIL", "two boards flashed with the same id",
         "EXIT", got[0] if isinstance(got, tuple) else got))

# every search must leave evidence in the log, including the ones that failed
got, logged = run({"COM20": ("identified", "2"), "COM22": ("claimed", None)})
ok = "searching for Lift 1: COM20=2 COM22=claimed" in logged
fails += 0 if ok else 1
print("%-4s %-52s %s" % ("ok" if ok else "FAIL",
                         "the search writes what it saw into the log",
                         logged.strip()[:70]))

print("\n%d failure(s)" % fails)
sys.exit(1 if fails else 0)
