"""port_resolver.py: early exit on identity, and parallel scanning.

Opens no serial port - serial.Serial is replaced with a fake that replays
bytes on a clock, so the timing claims can be checked without hardware.
"""
import os
import sys
import time

sys.path[0] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import port_resolver as pr

fails = 0


def check(name, ok, detail=""):
    global fails
    fails += 0 if ok else 1
    print("%-4s %-58s %s" % ("ok" if ok else "FAIL", name, detail))


class FakeSerial:
    """Hands out `script` as (delay_s, bytes) chunks, in real time."""

    def __init__(self, script):
        self.script = list(script)
        self.t0 = time.time()
        self.dtr = self.rts = True
        self.closed = False

    def reset_input_buffer(self):
        self.t0 = time.time()

    def read(self, n):
        if self.script and time.time() - self.t0 >= self.script[0][0]:
            return self.script.pop(0)[1]
        time.sleep(0.02)
        return b""

    def close(self):
        self.closed = True


def with_port(script, secs):
    made = []

    def factory(*a, **k):
        made.append(FakeSerial(script))
        return made[-1]

    real = pr.serial.Serial
    pr.serial.Serial = factory
    try:
        t = time.time()
        r = pr.probe("COMX", secs=secs)
        return r, time.time() - t, made[0]
    finally:
        pr.serial.Serial = real


BEACON = b"FW IODebug 1.2.2 2026-08-31 LIFT=5\n"

# 1. a beacon at 0.5s must end a 6s window almost at once
r, took, port = with_port([(0.5, b"ST 1000 FFFFFFF7F7FFF\n"), (0.6, BEACON)], secs=6)
check("identified port returns as soon as it names itself",
      r["state"] == "identified" and r["lift"] == "5" and took < 2.0,
      "%.2fs, state=%s" % (took, r["state"]))
check("the port is closed after an early exit", port.closed)

# 2. a beacon split across two reads must not be read as an answer early
r, took, _ = with_port([(0.3, b"FW IODebug 1.2.2 2026-08-31 LIFT="),
                        (1.2, b"5\n")], secs=6)
check("half a beacon is not an answer; the whole line is",
      r["state"] == "identified" and r["lift"] == "5" and took >= 1.1,
      "%.2fs" % took)

# 3. no identity -> still waits the full window before calling it
r, took, _ = with_port([(0.2, b"ST 1000 FFFFFFF7F7FFF\n")], secs=2)
check("a port that never names itself still gets the full window",
      r["state"] == "unidentified" and took >= 1.9, "%.2fs" % took)

# 4. firmware without LIFT= must not trigger the early exit
r, took, _ = with_port([(0.2, b"FW IODebug 1.1.0 2026-08-01\n")], secs=2)
check("a beacon with no LIFT= does not end the window",
      r["state"] == "unidentified" and took >= 1.9, "%.2fs" % took)

# 5. parallel scan: four 1s probes in about 1s, order preserved
def slow_probe(port):
    time.sleep(1.0)
    return {"port": port, "state": "identified", "lift": port[-1]}

ports = ["COM21", "COM20", "COM22", "COM14"]
t = time.time()
res = pr.scan(ports, probe_fn=slow_probe)
took = time.time() - t
check("four ports probed together, not one after another",
      took < 2.0, "%.2fs for 4 x 1.0s" % took)
check("results come back in the order the ports were given",
      [x["port"] for x in res] == ports)
check("an empty port list is an empty result", pr.scan([]) == [])

print("\n%d failure(s)" % fails)
sys.exit(1 if fails else 0)
