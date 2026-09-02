"""Decide why an RS485 link is not delivering, without transmitting a byte.

    python rs485_check.py COM3           # generic check
    python rs485_check.py COM3 1         # also insist the board says LIFT=1
    python rs485_check.py COM3 1 --secs 90

Five outcomes, because they send you to five different places:

  UP           valid protocol lines arrive and nearly all of the stream
               parses. Reports firmware and lift id.
  UP(DEGRADED) frames parse, but much of the stream does not. The link is
               carrying data and corrupting it. This is the one outcome
               that yields plausible wrong data instead of an obvious
               failure, so it is graded rather than waved through.
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

Both ends of that gap are measured, not assumed. Replaying 1.8 MB of
traffic three real boards actually produced -- 63,497 frames across
capture_lift_1.log and capture_lift_2.log -- gives 3.9% and 3.5%, with
zero lines rejected by the parser. The noise end came off the dead Lift 1
pair: 307 bytes over five runs, zero newlines, 0.0%. The threshold at 2%
sits clear of both.

The floor is set by the FW identity line, not by ST. Longest ST is 29 B
at millis maximum, just before the 49.7-day wrap, giving 3.45%; the
identity line is 36 B and gives 2.78%. FW dominates on a PARKED lift,
where nothing changes and the only traffic is the 30s identity beacon
and the 60s heartbeat -- a 45s window there is one FW line and nothing
else. So 2.78% is the real worst case, 0.78 points of headroom rather
than 1.45. A line would have to reach 50 B to fall through 2%, leaving
FW_VERSION and FW_DATE 14 B of slack between them.

KNOWN LIMITATION: a sender running at a baud outside SWEEP_BAUDS reads
as UNDRIVEN. The sweep short-circuits the moment any rate parses a
frame, so a standard rate is caught; a non-standard one is not, and its
mangled bytes carry no line structure to give it away. Harmless for this
project -- the firmware is fixed at 115200 -- but the verdict means "no
line protocol at any rate swept", which is narrower than "nobody is
transmitting".

AND UP MEANS AT LEAST ONE FRAME PARSED, not that the link is healthy.
An earlier version short-circuited unconditionally on the first good
frame, so a stream of 1 valid line among 200 corrupted ones reported
"UP -- the link is delivering" with "malformed state lines: 0"
underneath it. That count only ever saw lines that already parsed as ST,
so pure garbage never reached it and it printed a clean figure on a
nearly dead link -- the reassuring half of a self-contradicting report,
which is the half people act on. UP is graded on the unparseable share
now, and that share is stated in the verdict block itself rather than
only in the line above it.

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

# Attaching mid-stream clips the line in flight, and the window can close
# mid-line too, so up to two unparseable fragments are ordinary. Past that
# the link is corrupting content rather than just being joined late: Lift 2
# ran 60 hours and 55,516 lines with zero rejected.
ATTACH_JUNK = 2


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

DEGRADED_HELP = """
  Frames are getting through, so the board, its power and the A/B path
  are all fine. The line is corrupting content, which is worse than a
  dead link: it yields plausible wrong data rather than an obvious
  failure, and log_lift.py counts the bad lines as rejects but keeps the
  good ones. Do not start a capture on this. Check:
    1. Termination -- 120R at each far end of the pair, and only there.
    2. Cable length and routing at 115200. The shaft runs past VFDs
       switching high current; a long unterminated run picks that up.
    3. GND common between the module and the dongle. Without it the
       differential rides on whatever the two grounds differ by.
"""

SILENT_HELP = """
  Not one byte arrived, which is different from noise. Either the
  receive path is broken (dongle, cable, A/B open) or this dongle has
  fail-safe bias that parks an undriven bus at idle -- in which case a
  dead transmitter looks identical to silence. Confirm the dongle works
  by listening to a board known to be alive.
"""


def report_up(good, junk, want, secs):
    fw = [g for g in good if g.startswith("FW ")]
    st = [g for g in good if g.startswith("ST ")]
    total = len(good) + junk
    share = junk / total if total else 0.0
    degraded = junk > ATTACH_JUNK

    if degraded:
        print("\nVERDICT: UP (DEGRADED) -- frames parse, but most of the "
              "stream does not")
    else:
        print("\nVERDICT: UP -- the link is delivering")
    print("  parsed {} of {} lines, {} unparseable ({:.1f}%)".format(
        len(good), total, junk, 100 * share))

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
        # Only counts lines that already parsed as ST. It says nothing
        # about the stream as a whole, which is what the unparseable
        # share above is for -- keep the labels apart.
        bad = [s for s in st
               if len(s.split()) != 3 or len(s.split()[2]) != 13]
        print("  of those, {} carried a malformed mask".format(len(bad)))
    if degraded:
        print(DEGRADED_HELP)
        return 1
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
        return report_up(good, junk, want, secs)

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
