"""Decide why an RS485 link is not delivering, without transmitting a byte.

    python rs485_check.py COM3           # generic check
    python rs485_check.py COM3 1         # also insist the board says LIFT=1
    python rs485_check.py COM3 1 --secs 90

Four outcomes are worth telling apart, because they send you to four
different places with the multimeter:

  UP        valid protocol lines arrive. Reports firmware and lift id.
  SILENT    not one byte. The receive path itself is broken, or the
            dongle has fail-safe bias holding an undriven bus at idle.
  UNDRIVEN  bytes arrive but never form a frame, AND the byte rate rises
            with the baud rate. Nothing is transmitting: the UART is just
            digitising noise on a floating pair. See below.
  FRAMING   bytes arrive, never form a frame, but the byte rate stays put
            when the baud changes. Something IS transmitting and we are
            misreading it: wrong baud, or inverted A/B.

The UNDRIVEN vs FRAMING split is the whole point of this tool, and the
byte-rate test is what separates them. A real UART stream read at the
wrong baud still arrives at the sender's message rate -- the sender
decides when bytes exist. Noise has no message rate, so sampling it
faster simply yields more bytes. Sweep the baud and watch which one the
byte rate follows.

Polarity gets ruled out for free. With A and B swapped the idle line
reads as a continuous break, so the receiver emits 0x00 at the full line
rate -- about 11.5 kB/s at 115200. Noise on a floating pair trickles in
at a few bytes a second. The rate and the 0x00 count tell them apart.

Never transmits: RTS and DTR are held low so a direction-controlled
dongle stays in receive and cannot fight the bus. That matters here --
the boards are wired transmit-only (RS485_PLAN.md), so anything this end
put on the pair would collide with the Arduino with no arbitration.
"""
import sys
import time

import serial

from lift_decode import BAUD, lift_id, lift_label

SWEEP_BAUDS = [9600, 38400, 115200, 230400]
SWEEP_DWELL = 8.0
NOISE_RATE_RATIO = 4.0     # byte rate must rise this much to call it noise
BREAK_RATE = 2000.0        # bytes/s that says the line is stuck in break


def listen(port, baud, secs):
    """Collect raw bytes for a while. Sends nothing."""
    ser = serial.Serial()
    ser.port, ser.baudrate, ser.timeout = port, baud, 0.2
    ser.dtr = False
    ser.rts = False
    ser.open()
    time.sleep(0.2)
    ser.reset_input_buffer()
    data = bytearray()
    t0 = time.time()
    try:
        while time.time() - t0 < secs:
            chunk = ser.read(8192)
            if chunk:
                data += chunk
    finally:
        ser.close()
    return bytes(data), time.time() - t0


def frames(data):
    """Split into lines and keep the ones that look like our protocol."""
    good, junk = [], 0
    for raw in data.split(b"\n"):
        raw = raw.strip(b"\r")
        if not raw:
            continue
        if all(32 <= b < 127 for b in raw):
            txt = raw.decode("ascii")
            if txt.startswith("ST ") or txt.startswith("FW "):
                good.append(txt)
                continue
        junk += 1
    return good, junk


def describe(data, secs):
    n = len(data)
    printable = sum(1 for b in data if 32 <= b < 127 or b in (10, 13))
    return {
        "bytes": n,
        "rate": n / secs if secs else 0.0,
        "printable": 100.0 * printable / n if n else 0.0,
        "nulls": data.count(0),
        "newlines": data.count(10),
    }


def sweep(port):
    """Does the byte rate follow the sampling rate, or a sender?"""
    print("  no frame decoded -- sweeping baud to find out why")
    print("    {:>7} {:>7} {:>8} {:>7}".format("baud", "bytes", "B/s", "frames"))
    rates = []
    for baud in SWEEP_BAUDS:
        data, secs = listen(port, baud, SWEEP_DWELL)
        good, _ = frames(data)
        rate = len(data) / secs if secs else 0.0
        rates.append(rate)
        print("    {:>7} {:>7} {:>8.1f} {:>7}".format(
            baud, len(data), rate, len(good)))
        if good:
            return "FOUND", baud, good

    lo = next((r for r in rates if r > 0), 0.0)
    hi = rates[-1]
    if lo <= 0:
        return "FRAMING", None, []
    ratio = hi / lo
    baud_ratio = SWEEP_BAUDS[-1] / SWEEP_BAUDS[0]
    print("    byte rate rose {:.1f}x over a {:.0f}x baud range".format(
        ratio, baud_ratio))
    return ("UNDRIVEN" if ratio >= NOISE_RATE_RATIO else "FRAMING"), None, []


UNDRIVEN_HELP = """
  Nothing is driving the pair. Work outward from the board:

    1. Arduino power LED lit? A board that was running on USB has no
       supply once the cable comes out -- it needs its own adapter.
    2. MAX485 Vcc to GND reads 5V?
    3. DE and RE both strapped to 5V? If they float, the driver is off
       and the bus is undriven exactly like this.
    4. DI landing on DNMEGA1 terminal 1 (= D1 / TX0)?
    5. A and B continuous from the module through to the dongle, and
       GND common between them.

  One measurement settles 1-4 against 5: with the board idle and DE
  high, A minus B should sit around +2 to +5V (idle mark). Near 0V means
  no driver. A healthy differential that still yields noise here puts
  the fault in the wiring to the dongle instead.
"""

FRAMING_HELP = """
  Something is transmitting and we are misreading it. Check, in order:
    1. Both ends at 115200.
    2. A and B not swapped (see the 0x00 note in this file's docstring).
    3. Termination and cable length -- 115200 over a long unterminated
       run corrupts bits without changing the byte rate.
"""

SILENT_HELP = """
  Not one byte arrived, which is different from noise. Either the
  receive path is broken (dongle, cable, A/B open) or this dongle has
  fail-safe bias that parks an undriven bus at idle -- in which case a
  dead transmitter looks identical to silence. Confirm the dongle works
  by listening to a board known to be alive.
"""


def report_up(good, want, secs):
    fw = [g for g in good if g.startswith("FW ")]
    st = [g for g in good if g.startswith("ST ")]
    print("\nVERDICT: UP -- the link is delivering")
    if fw:
        print("  identity: " + fw[-1])
        if want:
            if "LIFT=" + want in fw[-1]:
                print("  board confirms it is Lift " + want)
            elif "LIFT=" in fw[-1]:
                print("  *** WRONG BOARD: wanted LIFT=" + want + " ***")
                return 2
            else:
                print("  firmware predates lift ids -- cannot confirm which board")
    else:
        print("  no identity line yet "
              "(beacon is every 30s, window was {:.0f}s)".format(secs))
    if st:
        print("  {} state lines, latest: {}".format(len(st), st[-1]))
        bad = [s for s in st
               if len(s.split()) != 3 or len(s.split()[2]) != 13]
        print("  malformed state lines: {}".format(len(bad)))
    return 0


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit(__doc__)
    port = args[0]
    want = lift_id(args[1]) if len(args) > 1 else None

    secs = 45.0
    if "--secs" in sys.argv:
        secs = float(sys.argv[sys.argv.index("--secs") + 1])

    who = ""
    if want:
        who = " expecting " + lift_label(want)
    print("{} @ {}, listening {:.0f}s{} -- transmitting nothing".format(
        port, BAUD, secs, who))

    data, elapsed = listen(port, BAUD, secs)
    info = describe(data, elapsed)
    good, junk = frames(data)

    print("  {} bytes, {:.1f} B/s, {:.0f}% printable, {} newlines".format(
        info["bytes"], info["rate"], info["printable"], info["newlines"]))
    print("  protocol lines {}, unusable lines {}".format(len(good), junk))

    if good:
        return report_up(good, want, secs)

    if info["bytes"] == 0:
        print("\nVERDICT: SILENT -- nothing arrived at all")
        print(SILENT_HELP)
        return 1

    if info["rate"] > BREAK_RATE and info["nulls"] > info["bytes"] * 0.5:
        print("\nVERDICT: FRAMING -- line is stuck in break, "
              "A and B look swapped")
        print(FRAMING_HELP)
        return 1

    print()
    kind, baud, found = sweep(port)
    if kind == "FOUND":
        print("\nVERDICT: FRAMING -- readable at {}, not at {}".format(
            baud, BAUD))
        print("  sample: " + found[0])
        print("  set both ends to the same rate.")
        return 1
    if kind == "UNDRIVEN":
        print("\nVERDICT: UNDRIVEN -- the byte rate follows the sampling rate,")
        print("  so this is noise on a pair nobody is driving. Nothing is")
        print("  transmitting; there is no signal here to misread.")
        print(UNDRIVEN_HELP)
        return 1
    print("\nVERDICT: FRAMING -- a sender is present but we cannot decode it")
    print(FRAMING_HELP)
    return 1


if __name__ == "__main__":
    sys.exit(main())
