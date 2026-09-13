"""Is this board running, and does it keep running?

    python board_alive.py COM3            # 15 min soak
    python board_alive.py COM3 --mins 60
    python board_alive.py COM3 --quick     # just prove it is alive now

Two failures look identical from the front of the cabinet, and the power
LED cannot tell them apart:

  RESTART  the board's millis() falls backwards. The supply dropped out,
           or the MCU rebooted. A marginal supply does this repeatedly.
  STALL    the 60s heartbeat simply stops arriving while the board is
           still powered. The sketch is no longer running. The LED stays
           lit throughout, so looking at the board proves nothing.

⚠️  OPENING THIS PORT CAN RESET THE BOARD, so a low uptime reading taken
just after connecting describes your own connection and not the board's
history. Measured on Lift 1: the first open after the USB cable is
plugged in resets it (uptime came back 0.1s), while a reopen moments
later does not (uptime carried straight on). Two conclusions were drawn
here from uptime figures that the act of measuring had created.

That has a consequence worth stating plainly: **USB cannot tell you
whether a board survived having its USB cable pulled.** Replugging and
reconnecting resets it, so "it lost power" and "you just reset it" both
read as uptime zero. Answer that question over RS485 from the Gateway,
or with a multimeter on the 5V pin, and use this tool for what it can
actually establish -- whether the board runs, and keeps running.

So this holds ONE connection open for the whole window and never
reopens. Every reopen would destroy the history it is measuring.
"""
import os
import re
import sys
import time
from datetime import datetime

# pyserial may live in the user profile, which a process started by the
# Scheduled Task cannot read - it dies on "import serial" before writing a
# line. A copy next to this file on D: is reachable from every context:
#     pip install --target vendor pyserial
_vendor = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor")
if os.path.isdir(_vendor) and _vendor not in sys.path:
    sys.path.insert(0, _vendor)

import serial

from lift_decode import BAUD

HEARTBEAT_S = 60.0
STALL_AFTER = 75.0      # heartbeat plus slack, so a busy lift never trips it
FRESH_BOOT_MS = 5000    # below this, the board has just started

ST = re.compile(r"^ST (\d+) ([0-9A-F]{13})$")
FW = re.compile(r"^FW IODebug .*$")


def open_quietly(port):
    """Open without asserting the control lines. Sends nothing."""
    ser = serial.Serial()
    ser.port, ser.baudrate, ser.timeout = port, BAUD, 0.2
    ser.dtr = False
    ser.rts = False
    ser.open()
    ser.reset_input_buffer()
    return ser


def soak(port, minutes):
    ser = open_quietly(port)
    t0 = time.time()
    end = t0 + minutes * 60
    buf = b""
    first = None
    last_ms = None
    last_seen = t0
    restarts, stalls = [], []
    n_st = n_fw = 0
    ident = set()

    print("{}: holding one connection for {:.0f} min".format(port, minutes))
    print("  restart = board clock falls back;  "
          "stall = no line for {:.0f}s".format(STALL_AFTER))
    print("  started {:%H:%M:%S}\n".format(datetime.now()), flush=True)

    while time.time() < end:
        chunk = ser.read(512)
        now = time.time()
        if now - last_seen > STALL_AFTER:
            stalls.append(now - t0)
            print("  [{:7.1f}s] *** STALL: nothing for {:.0f}s ***".format(
                now - t0, now - last_seen), flush=True)
            last_seen = now
        if not chunk:
            continue
        buf += chunk
        while b"\n" in buf:
            raw, buf = buf.split(b"\n", 1)
            line = raw.strip(b"\r").decode("ascii", "replace")
            if FW.match(line):
                n_fw += 1
                ident.add(line)
                last_seen = now
                continue
            m = ST.match(line)
            if not m:
                continue
            n_st += 1
            last_seen = now
            ms = int(m.group(1))
            if first is None:
                first = (ms, now)
                note = " -- board had just started" if ms < FRESH_BOOT_MS else ""
                print("  [{:7.1f}s] first line, board uptime {:.1f}s{}".format(
                    now - t0, ms / 1000.0, note), flush=True)
            if last_ms is not None and ms < last_ms:
                restarts.append(now - t0)
                print("  [{:7.1f}s] *** RESTART: {:.1f}s -> {:.1f}s ***".format(
                    now - t0, last_ms / 1000.0, ms / 1000.0), flush=True)
            last_ms = ms
    ser.close()

    print("\n  ended {:%H:%M:%S} after {:.1f} min".format(
        datetime.now(), (time.time() - t0) / 60))
    for i in sorted(ident):
        print("  identity: " + i)
    print("  state lines {}, identity lines {}".format(n_st, n_fw))
    print("  restarts {}   stalls {}".format(len(restarts), len(stalls)))

    if first is None or last_ms is None:
        print("\nVERDICT: the board never spoke. It is not running, or "
              "nothing on this port is.")
        return 1

    board = (last_ms - first[0]) / 1000.0
    wall = time.time() - first[1]
    print("  board clock advanced {:.1f}s against {:.1f}s of PC time "
          "(drift {:+.1f}s, {:+.1f}%)".format(
              board, wall, board - wall,
              100 * (board - wall) / wall if wall else 0))

    if restarts:
        print("\nVERDICT: the board REBOOTED while connected, {} time(s).\n"
              "  Look at the supply: a marginal rail browns the MCU out and\n"
              "  the power LED stays lit right through it.".format(len(restarts)))
        return 1
    if stalls:
        print("\nVERDICT: the board went QUIET while still powered, {} "
              "time(s).\n  The sketch stopped running. This is the failure "
              "that looks\n  perfectly healthy from the front of the "
              "cabinet.".format(len(stalls)))
        return 1
    print("\nVERDICT: ALIVE -- ran the whole window without a break.")
    return 0


def quick(port):
    """Prove it is talking right now, and that its clock advances."""
    ser = open_quietly(port)
    t0 = time.time()
    buf = b""
    seen = []
    ident = None
    while time.time() - t0 < STALL_AFTER + 20 and len(seen) < 2:
        chunk = ser.read(512)
        if not chunk:
            continue
        buf += chunk
        while b"\n" in buf:
            raw, buf = buf.split(b"\n", 1)
            line = raw.strip(b"\r").decode("ascii", "replace")
            if FW.match(line):
                ident = line
                print("  [{:%H:%M:%S}] {}".format(datetime.now(), line))
            m = ST.match(line)
            if m:
                seen.append((int(m.group(1)), time.time()))
                print("  [{:%H:%M:%S}] {}".format(datetime.now(), line))
    ser.close()

    if not seen:
        print("\nVERDICT: NO RESPONSE in {:.0f}s, longer than the {:.0f}s "
              "heartbeat.".format(STALL_AFTER + 20, HEARTBEAT_S))
        return 1
    print("\n  board uptime {:.1f}s".format(seen[0][0] / 1000.0))
    if ident:
        print("  identity {}".format(ident))
    if len(seen) >= 2:
        db = (seen[1][0] - seen[0][0]) / 1000.0
        dw = seen[1][1] - seen[0][1]
        print("  clock advancing {:.1f}s board vs {:.1f}s PC".format(db, dw))
        if abs(db - dw) > 2.0:
            print("\nVERDICT: talking, but its clock does not track real "
                  "time. Suspect the board.")
            return 1
    if seen[0][0] < FRESH_BOOT_MS:
        print("\n  note: uptime is near zero, so the board started just now."
              "\n  Opening this port can do that -- see the header. Do not"
              "\n  read it as evidence about what happened before you"
              "\n  connected.")
    print("\nVERDICT: ALIVE -- the board is running and answering.")
    return 0


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit(__doc__)
    port = args[0]
    if "--quick" in sys.argv:
        return quick(port)
    mins = 15.0
    if "--mins" in sys.argv:
        mins = float(sys.argv[sys.argv.index("--mins") + 1])
    return soak(port, mins)


if __name__ == "__main__":
    sys.exit(main())
