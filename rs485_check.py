"""Decide why an RS485 link is not delivering, without transmitting a byte.

    python rs485_check.py COM3           # generic check
    python rs485_check.py COM3 1         # also insist the board says LIFT=1
    python rs485_check.py COM3 1 --secs 90

Five outcomes, because they send you to five different places:

  UP           valid protocol lines arrive. Reports firmware and lift id.
  SILENT       not one byte anywhere.
  UNDRIVEN     bytes arrive but carry no line structure at any rate.
               Nothing is transmitting; the UART is digitising noise on a
               floating pair.
  FRAMING      bytes arrive WITH line structure, but no line parses. A
               sender is present and we are misreading it.
  INCONCLUSIVE too few bytes to tell those two apart. Rerun longer.

Deciding between UNDRIVEN and FRAMING is the whole point, so it is worth
saying exactly what the test is and why an earlier version of it was
wrong.

WHAT DECIDES IT: line structure, measured as the share of bytes that are
0x0A. Our protocol emits about one newline per 28 bytes, so 3.6%. Uniform
random bytes yield 1/256, so 0.4%. An order of magnitude apart, and it
needs no assumption about anyone's timing.

WHAT DOES NOT DECIDE IT: the byte rate rising with the baud rate. The
reasoning is sound -- a real sender fixes when bytes exist, whereas noise
has no message rate, so sampling it faster just yields more of it -- and
the ratio is still reported below as corroboration. But noise arrives in
bursts, so whether an 8s dwell catches one is luck, and a verdict
computed by dividing two lucky numbers is luck too. Run against one dead
link it returned FRAMING, then UNDRIVEN three times with ratios of 57,
59 and 14, then SILENT: five runs, four verdicts, nothing touched. Two
faults made it worse than the raw variance -- the low end was taken as
the first non-zero rate rather than the smallest, so a high first reading
deflated the ratio directly into the wrong branch, and single-digit byte
counts were being divided at all. Both are fixed here, but the ratio is
corroboration now and never the verdict.

Polarity gets ruled out separately and for free. With A and B swapped the
idle line reads as a continuous break, so the receiver emits 0x00 at the
full line rate -- about 11.5 kB/s at 115200. Noise on a floating pair
trickles in at a few bytes a second. Rate and 0x00 count separate them.

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

# Our protocol runs about 1 newline per 28 bytes (3.6%); uniform random
# bytes give 1/256 (0.4%). Anything at or above this is line-structured.
LINE_SHARE = 0.02

# Below this many bytes, absence of newlines proves nothing: at 3.6% a
# real stream would still show none about 0.4% of the time at 150 bytes,
# and far more often below that. Refuse to rule instead of guessing.
MIN_EVIDENCE = 150

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


class Evidence:
    """Bytes and newlines pooled across every dwell, at every baud.

    Pooled deliberately. Each individual dwell is too small to rule on,
    and the line-structure test does not care which rate the bytes came
    in at: a sender at any swept rate contributes newlines, noise at
    every rate contributes almost none.
    """

    def __init__(self):
        self.bytes = 0
        self.newlines = 0
        self.nulls = 0
        self.rates = []

    def add(self, data, secs):
        self.bytes += len(data)
        self.newlines += data.count(10)
        self.nulls += data.count(0)
        self.rates.append(len(data) / secs if secs else 0.0)

    @property
    def line_share(self):
        return self.newlines / self.bytes if self.bytes else 0.0

    def rate_ratio(self):
        """Corroboration only. Smallest non-zero rate against the largest."""
        nz = [r for r in self.rates if r > 0]
        if len(nz) < 2:
            return None
        return max(nz) / min(nz)


def sweep(port, ev):
    """Look for line structure at any standard rate, pooling the evidence."""
    print("  no frame decoded -- sweeping baud")
    print("    {:>7} {:>7} {:>8} {:>4} {:>7}".format(
        "baud", "bytes", "B/s", "LF", "frames"))
    for baud in SWEEP_BAUDS:
        data, secs = listen(port, baud, SWEEP_DWELL)
        good, _ = frames(data)
        ev.add(data, secs)
        print("    {:>7} {:>7} {:>8.1f} {:>4} {:>7}".format(
            baud, len(data), len(data) / secs if secs else 0.0,
            data.count(10), len(good)))
        if good:
            return good, baud
    return [], None


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
       run corrupts bits without changing the line structure.
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


def report_structure(ev):
    """Print the line-structure evidence the verdict actually rests on."""
    print("\n  evidence pooled over every dwell:")
    print("    {} bytes, {} newlines -> {:.1f}% line structure "
          "(protocol ~3.6%, noise ~0.4%)".format(
              ev.bytes, ev.newlines, 100 * ev.line_share))
    ratio = ev.rate_ratio()
    if ratio is not None:
        span = SWEEP_BAUDS[-1] / SWEEP_BAUDS[0]
        print("    byte rate spread {:.1f}x over a {:.0f}x baud range "
              "(corroboration only)".format(ratio, span))


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

    ev = Evidence()
    data, elapsed = listen(port, BAUD, secs)
    ev.add(data, elapsed)
    good, junk = frames(data)

    print("  {} bytes, {:.1f} B/s, {} newlines".format(
        len(data), ev.rates[0], data.count(10)))
    print("  protocol lines {}, unusable lines {}".format(len(good), junk))

    if good:
        return report_up(good, want, secs)

    if ev.rates[0] > BREAK_RATE and ev.nulls > ev.bytes * 0.5:
        print("\nVERDICT: FRAMING -- line is stuck in break, "
              "A and B look swapped")
        print(FRAMING_HELP)
        return 1

    print()
    found, baud = sweep(port, ev)
    if found:
        report_structure(ev)
        print("\nVERDICT: FRAMING -- readable at {}, not at {}".format(
            baud, BAUD))
        print("  sample: " + found[0])
        print("  set both ends to the same rate.")
        return 1

    if ev.bytes == 0:
        print("\nVERDICT: SILENT -- nothing arrived at any rate")
        print(SILENT_HELP)
        return 1

    report_structure(ev)

    if ev.line_share >= LINE_SHARE:
        print("\nVERDICT: FRAMING -- the stream has line structure but no")
        print("  line parses, so a sender is present and we are misreading it.")
        print(FRAMING_HELP)
        return 1

    if ev.bytes < MIN_EVIDENCE:
        print("\nVERDICT: INCONCLUSIVE -- too few bytes to rule.")
        print("  No line structure was seen, but {} bytes is not enough for".format(ev.bytes))
        print("  that absence to mean anything. Rerun with --secs 120 before")
        print("  sending anyone to check wiring.")
        return 1

    print("\nVERDICT: UNDRIVEN -- bytes arrive but carry no line structure")
    print("  at any rate swept, so no ASCII line protocol is present. The")
    print("  UART is digitising noise on a pair nobody is driving; there is")
    print("  no signal here to misread.")
    print(UNDRIVEN_HELP)
    return 1


if __name__ == "__main__":
    sys.exit(main())
