"""
Announce the moment a serial port appears or disappears.

    python watch_ports.py [seconds]

For plugging a board in and getting an answer straight away, rather than
asking someone to re-run a check after every attempt. Reports arrivals and
removals with a timestamp, and says nothing while nothing changes.
"""
import sys
import time

from serial.tools import list_ports

SECONDS = int(sys.argv[1]) if len(sys.argv) > 1 else 180


def snapshot():
    return {p.device: (p.description, p.location) for p in list_ports.comports()}


prev = snapshot()
print(f"watching for {SECONDS}s. Ports present now:")
for dev, (desc, loc) in sorted(prev.items()):
    print(f"    {dev:8} {desc}  loc={loc}")
print("\n  plug the board in - anything that changes is reported here\n" + "-" * 58)

end = time.time() + SECONDS
while time.time() < end:
    time.sleep(0.4)
    now = snapshot()
    for dev in sorted(set(now) - set(prev)):
        desc, loc = now[dev]
        print(f"  {time.strftime('%H:%M:%S')}  APPEARED  {dev}  {desc}  loc={loc}")
    for dev in sorted(set(prev) - set(now)):
        print(f"  {time.strftime('%H:%M:%S')}  REMOVED   {dev}")
    prev = now

print("-" * 58)
print("  finished. Ports present:", ", ".join(sorted(prev)) or "none")
