"""Ask every unclaimed port which lift is on it, and report the map.

    python port_resolver.py              scan and print the map
    python port_resolver.py --json       same, machine readable

Built for the case where somebody has unplugged the dongles and put them back
in different sockets. CH340 adapters carry no USB serial number, so Windows
names their ports by which socket they sit in - the numbers move and the only
durable identity is the one each board announces itself: a line reading
"FW IODebug <ver> <date> LIFT=<n>", repeated every 30 seconds.

SAFE ALONGSIDE RUNNING CAPTURES. Windows opens a COM port exclusively, so a
port a logger is recording on refuses this scanner with PermissionError while
a port that has gone away refuses with FileNotFoundError. The two are
distinguishable, so a held port is reported as claimed and never touched, and
a scan can never steal a live capture. Nothing is ever transmitted: the boards
are wired transmit-only and drive their pair continuously, so anything sent
would collide.

This resolves; it does not rebind. Which lift a log belongs to stays a human
decision, because finding a foreign board on a port is one negative fact and
does not say whether somebody moved a plug or a dongle died.
"""
import os
import json
import re
import sys
import time

# pyserial may live in the user profile, which a process started by the
# Scheduled Task cannot read - it dies on "import serial" before writing a
# line. A copy next to this file on D: is reachable from every context:
#     pip install --target vendor pyserial
_vendor = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor")
if os.path.isdir(_vendor) and _vendor not in sys.path:
    sys.path.insert(0, _vendor)

import serial
from serial.tools import list_ports

BAUD = 115200
PROBE_S = 40.0          # the identity beacon repeats every 30s
FW = re.compile(r"FW IODebug (\S+) (\S+)(?: LIFT=(\d+))?")
ST = re.compile(r"^ST (\d+) ([0-9A-Fa-f]{13})$")


def probe(port, secs=PROBE_S):
    """Listen without transmitting. Returns a dict describing what is there."""
    try:
        ser = serial.Serial(port, BAUD, timeout=0.5)
    except serial.SerialException as e:
        txt = str(e)
        if "PermissionError" in txt or "Access is denied" in txt:
            return {"port": port, "state": "claimed",
                    "note": "a capture is recording on this port"}
        if "FileNotFoundError" in txt or "cannot find" in txt:
            return {"port": port, "state": "gone",
                    "note": "the port no longer exists"}
        return {"port": port, "state": "error", "note": txt[:90]}

    ser.dtr = False
    ser.rts = False
    time.sleep(0.2)
    ser.reset_input_buffer()
    raw = bytearray()
    end = time.time() + secs
    while time.time() < end:
        raw += ser.read(512)
        # Stop as soon as the board has named itself. Waiting out the full
        # window is only needed to call a port *unidentified*; an identified
        # one is settled the moment its beacon lands. Only complete lines
        # count, so a beacon cut off mid-number is never read as an answer.
        done = raw[:raw.rfind(b"\n") + 1].decode("utf-8", "replace")
        if any(m and m.group(3) for m in (FW.search(l) for l in done.splitlines())):
            break
    ser.close()

    lines = [l.strip() for l in raw.decode("utf-8", "replace").splitlines()
             if l.strip()]
    fw = [m for m in (FW.search(l) for l in lines) if m]
    st = [m for m in (ST.match(l) for l in lines) if m]

    if fw and fw[-1].group(3):
        return {"port": port, "state": "identified", "lift": fw[-1].group(3),
                "firmware": f"{fw[-1].group(1)} {fw[-1].group(2)}",
                "uptime_ms": int(st[-1].group(1)) if st else None,
                "st_lines": len(st)}
    if fw:
        return {"port": port, "state": "unidentified", "st_lines": len(st),
                "firmware": f"{fw[-1].group(1)} {fw[-1].group(2)}",
                "note": "board announces itself but carries no LIFT= field "
                        "(firmware older than 1.2.0, or built without "
                        "-DLIFT_ID) - it cannot be bound automatically"}
    if st:
        return {"port": port, "state": "unidentified", "st_lines": len(st),
                "note": f"{len(st)} state lines but no identity in {secs:.0f}s "
                        f"- longer than the 30s beacon, so this board cannot "
                        f"name itself"}
    return {"port": port, "state": "silent", "bytes": len(raw),
            "note": f"{len(raw)} bytes, no protocol - nothing is driving this "
                    f"pair" if raw else "not one byte arrived"}


def scan(ports, probe_fn=None):
    """Probe every port at once and return the results in the order given.

    One after another, each unclaimed port costs up to PROBE_S, so a reboot
    with four free ports spent 2 min 43 s here before a single capture could
    start (measured 13 Sep 2026: logon 09:24:07, task 09:24:24, scan done
    09:27:09). The ports are independent devices and every probe only
    listens, so probing them together costs one beacon interval in total.
    """
    probe_fn = probe_fn or probe
    if not ports:
        return []
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=len(ports)) as pool:
        return list(pool.map(probe_fn, ports))


def main():
    ports = [p.device for p in list_ports.comports()
             if "CH340" in (p.description or "") or "USB" in (p.description or "")]
    if not ports:
        sys.exit("no USB serial adapters found")

    if "--json" not in sys.argv:
        print(f"probing {len(ports)} port(s) in parallel - up to {PROBE_S:.0f}s on the "
              f"unclaimed ones, transmitting nothing\n")

    results = scan(ports)

    if "--json" in sys.argv:
        print(json.dumps(results, indent=2))
        return

    width = max(len(r["port"]) for r in results)
    for r in results:
        p = r["port"].ljust(width)
        if r["state"] == "identified":
            up = f"{r['uptime_ms']/3600000:.1f}h" if r.get("uptime_ms") else "?"
            print(f"  {p}  LIFT={r['lift']}   {r['firmware']}   "
                  f"uptime {up}   {r['st_lines']} state lines")
        elif r["state"] == "claimed":
            print(f"  {p}  in use    {r['note']}")
        else:
            print(f"  {p}  {r['state']:<9} {r.get('note','')}")

    found = {r["lift"]: r["port"] for r in results if r["state"] == "identified"}
    if found:
        print("\n  to record these:")
        for lift in sorted(found):
            print(f"    python log_lift.py {found[lift]} {lift} --listen")


if __name__ == "__main__":
    main()
