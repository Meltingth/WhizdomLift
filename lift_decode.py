"""
Decode the lift's position and status signals from the IODebug watch stream.

    python lift_decode.py learn [seconds]   watch the bits move and infer the mapping
    python lift_decode.py                   decode live using the mapping below

--------------------------------------------------------------------------
The signals, read off the controller diagram
--------------------------------------------------------------------------

Position (位置信号编码), 6 relay contacts, terminals 1-7, common on terminal 1:

    terminal 2 = VS2   ALR0 / MC-10   bit 0   weight  1
    terminal 3 = VS3   ALR1 / MC-9    bit 1   weight  2
    terminal 4 = VS4   ALR2 / MC-8    bit 2   weight  4
    terminal 5 = VS5   ALR3 / MC-7    bit 3   weight  8
    terminal 6 = VS6   ALR4 / MC-6    bit 4   weight 16
    terminal 7 = VS7   ALR5 / MC-5    bit 5   weight 32

The encoder table in the diagram is plain binary with VS2 as the least
significant bit - floor 14 is 001110 = 8+4+2, floor 32 is 100000. So:

    floor = VS7*32 + VS6*16 + VS5*8 + VS4*4 + VS3*2 + VS2*1

Status, 6 relay contacts, commons on terminals 13 and 19:

    terminal 14  RUNNING   运行
    terminal 15  FAILURE   安全   (safety)
    terminal 16  FIRE      火灾
    terminal 17  UP        上行
    terminal 18  DN        下行
    terminal 20  FIRE RETURN

--------------------------------------------------------------------------
Sense
--------------------------------------------------------------------------
These are dry relay contacts read with INPUT_PULLUP, so a CLOSED contact pulls
the pin LOW. Active = 0 on the wire. ACTIVE_LOW below handles the inversion;
set it False only if the contacts are wired to a high side instead.
"""
import re
import sys
import time

import serial

PORT = "COM3"
BAUD = 115200
DIG_FIRST = 2                 # bit 0 of the mask is D2, matching the sketch

ACTIVE_LOW = True

# Fill these in once the wiring is known - "learn" mode prints them for you.
#   POSITION_BITS: {arduino_pin: bit_index}   bit 0 = VS2 = least significant
#   STATUS_PINS:   {arduino_pin: label}
# Confirmed on the fast-sampling capture: 729 stable states, 100% single-step,
# codes 1..46. All six encoder lines reach the Arduino, including VS7.
#
# History: an earlier 5-bit map ({25:0 .. 29:4}, "top floor 23") was wrong.
# The first sketch printed EDGE/snapshot text while capturing; those prints
# blocked the sampling loop long enough to alias D24 - the fastest-toggling
# line - into looking like a once-per-floor strobe. Every wire was then
# credited one bit position too high, and the decoded top (23) was exactly the
# true code (46) shifted right by one bit.
POSITION_BITS = {24: 0, 25: 1, 26: 2, 27: 3, 28: 4, 29: 5}   # VS2..VS7

# Lift B (COM5): D24 never reads LOW - its VS2 line is dead, so only bits
# 1..5 arrive and the decodable value is the true code shifted right once.
# The remaining five wires land on the same pins as lift A.
POSITION_BITS_B = {25: 0, 26: 1, 27: 2, 28: 3, 29: 4}        # = true code >> 1

# Code <-> floor-label calibration, from operator-timed stops on lift A.
# Constant +2 from label 20 upward; the ladder below floor 9 is not yet
# fully pinned (needs one observed stop at each of 2..8).
#   B1->1  1->2  9->12  20->22  26->28  32->34  33->35  36->38  37->39  44->46
# The offset shrinking +3 -> +2 between 9 and 20 confirms label 19 has no
# physical landing. Labels 7 and 19 are skipped per the operator.
CODE_TO_LABEL = {1: "B1", 2: "1", 12: "9", 22: "20", 28: "26", 34: "32",
                 35: "33", 38: "36", 39: "37", 46: "44"}

# Resolved by correlating each line against what the car was doing, over 9
# journeys covering 115s of upward travel, 135s of downward and 994s stopped:
#
#   pin      UP    DOWN   STOPPED
#   D16    100%    100%       12%   closed whenever moving, open at rest
#   D17    100%    100%      100%   never opens
#   D19    100%      0%       41%   upward travel only
#   D20      0%    100%        7%   downward travel only
#   D24     51%     51%       13%   ~50% duty while moving - a per-floor pulse
STATUS_PINS = {
    16: "RUNNING",     # 运行
    17: "SAFETY",      # 安全 - normally closed, opens on a fault
    19: "UP",          # 上行
    20: "DN",          # 下行
}

# Never seen closed, so their pins are still unknown - an open contact is
# indistinguishable from an unconnected pin:
#   VS7 (bit 5)   would need the encoder to pass 31; it peaks at 23
#   FIRE 火灾, FIRE RETURN   only close in an alarm condition

# ---------------------------------------------------------------- lift names
# The building numbers its lifts 1..5. During testing they were reached in a
# different order and labelled A..E, and those letters are baked into the
# capture logs and the report, so both spellings have to keep working.
#
#   working label   building name   capture file
#         A            Lift 3       capture_lift_3.log   (reference wiring)
#         B            Lift 1       capture_lift_1.log   (VS2 line dead)
#         C            Lift 2       capture_lift_2.log
#         D            Lift 4       capture_lift_4.log
#         E            Lift 5       capture_lift_5.log   (number inferred:
#                                   the only one left once 1-4 are assigned)
LIFT_ALIAS = {"A": "3", "B": "1", "C": "2", "D": "4", "E": "5"}
LEGACY_LABEL = {v: k for k, v in LIFT_ALIAS.items()}


def lift_id(token):
    """Accept 'C', 'lift 2', '2' - return the building lift number as a string."""
    t = str(token).upper().replace("LIFT", "").replace("#", "").strip()
    return LIFT_ALIAS.get(t, t)


def lift_log(token):
    """Capture filename for a lift, given either spelling of its name."""
    return f"capture_lift_{lift_id(token)}.log"


def lift_label(token):
    """Human label, e.g. 'Lift 2 (C)'."""
    n = lift_id(token)
    old = LEGACY_LABEL.get(n)
    return f"Lift {n}" + (f" ({old})" if old else "")



# ------------------------------------------------------- per-pin debouncing
def debounce_pins(rows, hold_ms=60, settle_ms=150, npins=52, first_pin=2):
    """Rebuild the state timeline, settling each pin on its own.

    rows: [(clock, board_ms, frozenset_of_low_pins)] straight from a capture.

    Filtering whole states by how long they persist fails as soon as ONE line
    chatters: a contact bouncing at mains frequency makes every combined state
    shorter than the threshold, so a capture with nine clean signals and one
    noisy one is thrown away entirely. Lift 2 produced 132,696 samples and only
    six surviving states that way.

    Debouncing each pin separately keeps the clean lines intact and discards
    only the noise on the offending one: a pin's transition counts only if the
    new level then holds for hold_ms.
    """
    if not rows:
        return []

    # A capture log accumulates sessions, and the board's millisecond counter
    # restarts at zero each time it is reset. Left alone, that makes durations
    # go negative across the seam and manufactures impossible states - Lift 3
    # briefly decoded as code 63, every position bit closed at once. Split the
    # log wherever board time steps backwards and settle each run separately.
    segments, start = [], 0
    for i in range(1, len(rows)):
        if rows[i][1] < rows[i - 1][1]:
            segments.append(rows[start:i])
            start = i
    segments.append(rows[start:])
    if len(segments) > 1:
        out = []
        for seg in segments:
            out.extend(debounce_pins(seg, hold_ms, settle_ms, npins, first_pin))
        return out

    # transitions per pin
    per = {p: [] for p in range(first_pin, first_pin + npins)}
    prev = None
    for clock, t, low in rows:
        for p in per:
            lvl = p in low                     # True = contact closed (LOW)
            if prev is None or (p in prev) != lvl:
                per[p].append((t, lvl))
        prev = low

    # keep a transition only if its level survives hold_ms
    events = []
    for p, trans in per.items():
        settled = None
        for i, (t, lvl) in enumerate(trans):
            nxt = trans[i + 1][0] if i + 1 < len(trans) else t + hold_ms + 1
            if nxt - t < hold_ms and settled is not None:
                continue                       # glitch: too brief to be real
            if lvl != settled:
                events.append((t, p, lvl))
                settled = lvl

    events.sort(key=lambda e: e[0])
    clock_at = {t: c for c, t, _ in rows}

    # Replay the accepted events. Two levels of coalescing are needed and they
    # fix different faults:
    #   - events sharing a timestamp are applied together, so a simultaneous
    #     multi-bit change yields one state rather than one per bit;
    #   - a composite state that does not then last settle_ms is dropped,
    #     because relay contacts within a group do not switch on the same
    #     millisecond and the few-ms straddle is a bogus intermediate code.
    raw_states, cur = [], set()
    i = 0
    while i < len(events):
        t = events[i][0]
        while i < len(events) and events[i][0] == t:
            _, p, lvl = events[i]
            cur.add(p) if lvl else cur.discard(p)
            i += 1
        snap = frozenset(cur)
        if raw_states and raw_states[-1][2] == snap:
            continue
        raw_states.append((clock_at.get(t, ""), t, snap))

    states = []
    for k, (clock, t, snap) in enumerate(raw_states):
        dur = (raw_states[k + 1][1] - t) if k + 1 < len(raw_states) else settle_ms
        if dur < settle_ms:
            continue
        if states and states[-1][2] == snap:
            continue
        states.append((clock, t, snap))
    return states


VS_NAME = {0: "VS2", 1: "VS3", 2: "VS4", 3: "VS5", 4: "VS6", 5: "VS7"}
ST_RE = re.compile(r"^ST (\d+) ([0-9A-Fa-f]+)")


def open_watch():
    ser = serial.Serial(PORT, BAUD, timeout=0.2)
    ser.dtr = False
    ser.rts = False
    time.sleep(0.2)
    ser.reset_input_buffer()
    time.sleep(1.5)
    ser.write(b"w")               # enable watch mode
    ser.flush()
    return ser


def stream(ser, seconds):
    """Yield (millis, mask) for each ST line, until `seconds` elapse."""
    buf = b""
    end = time.time() + seconds if seconds else None
    while end is None or time.time() < end:
        buf += ser.read(512)
        while b"\n" in buf:
            line, buf = buf.split(b"\n", 1)
            m = ST_RE.match(line.decode("utf-8", "replace").strip())
            if m:
                yield int(m.group(1)), int(m.group(2), 16)


def active(mask, pin):
    """True when the contact for `pin` is closed."""
    bit = (mask >> (pin - DIG_FIRST)) & 1
    return bit == 0 if ACTIVE_LOW else bit == 1


def decode_floor(mask, bits):
    floor = 0
    for pin, idx in bits.items():
        if active(mask, pin):
            floor |= 1 << idx
    return floor


# ----------------------------------------------------------------- learn

def learn(seconds):
    """Infer which pins are the position bits from how often each one toggles.

    On a lift moving floor by floor the position code counts in binary, so the
    least significant bit flips on every single floor, the next on every second
    floor, then every fourth, and so on. Ranking the pins by how often they
    toggle therefore recovers the bit order directly.

    A trip that never goes above floor 15 leaves VS6 and VS7 permanently 0, so
    those pins will not appear. That is expected, and is reported rather than
    guessed at.
    """
    print(f"Learning for {seconds}s - move the lift through as many floors as you can.\n")
    ser = open_watch()

    toggles = {}
    samples = []
    prev = None
    for t, mask in stream(ser, seconds):
        samples.append((t, mask))
        if prev is not None:
            diff = prev ^ mask
            for i in range(52):
                if diff >> i & 1:
                    toggles[i + DIG_FIRST] = toggles.get(i + DIG_FIRST, 0) + 1
        prev = mask
        changed = ", ".join(f"D{p}" for p in sorted(toggles)) or "-"
        print(f"\r  {len(samples):4d} changes seen   active pins: {changed}   ",
              end="", flush=True)
    ser.close()
    print("\n")

    if not toggles:
        print("No pin changed at all. Either the lift did not move, or the")
        print("Mega is not connected to the relay outputs yet.")
        return

    ranked = sorted(toggles.items(), key=lambda kv: -kv[1])
    print("Toggle counts (most active first):")
    for pin, n in ranked:
        print(f"   D{pin:<3} {n:5d}")

    pos = ranked[:6]
    print("\nProposed position bits, LSB first:")
    guess = {}
    for idx, (pin, n) in enumerate(pos):
        guess[pin] = idx
        print(f"   D{pin:<3} -> bit {idx}  ({VS_NAME[idx]}, weight {1 << idx})")

    # A correct bit order makes consecutive floor readings differ by one.
    steps = [decode_floor(m, guess) for _, m in samples]
    deltas = [abs(b - a) for a, b in zip(steps, steps[1:]) if b != a]
    ok = sum(1 for d in deltas if d == 1)
    if deltas:
        pct = 100 * ok / len(deltas)
        print(f"\nSanity check: {ok}/{len(deltas)} floor changes were a single "
              f"step ({pct:.0f}%)")
        print("  >70% means the bit order is right."
              if pct > 70 else
              "  Low - travel more floors, or some bits were never exercised.")
        print(f"  floors seen: {sorted(set(steps))}")

    print("\nPaste into the configuration at the top of this file:")
    print(f"POSITION_BITS = {guess}")
    rest = [p for p, _ in ranked[6:]]
    if rest:
        print(f"STATUS_PINS = {{{', '.join(f'{p}: \"?\"' for p in rest)}}}"
              "   # label these from the diagram")


# ---------------------------------------------------------------- decode

def decode():
    if not POSITION_BITS:
        print("POSITION_BITS is empty - run 'python lift_decode.py learn' first.")
        return

    print("Decoding. Ctrl-C to stop.\n")
    print(f"{'time':>9}  {'floor':>5}  bits    status")
    print("-" * 62)
    ser = open_watch()
    last = None
    try:
        for t, mask in stream(ser, None):
            floor = decode_floor(mask, POSITION_BITS)
            bits = "".join(
                "1" if any(active(mask, p) for p, i in POSITION_BITS.items() if i == b)
                else "0"
                for b in range(5, -1, -1))
            flags = [name for pin, name in STATUS_PINS.items() if active(mask, pin)]
            line = (f"{t / 1000:9.2f}  {floor:5d}  {bits}  "
                    f"{' '.join(flags) if flags else '-'}")
            if line[11:] != (last or "")[11:]:      # skip pure timestamp churn
                arrow = ""
                if last:
                    prev_floor = int(last[11:16])
                    if floor > prev_floor:
                        arrow = "  UP"
                    elif floor < prev_floor:
                        arrow = "  DOWN"
                print(line + arrow)
            last = line
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        ser.close()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "learn":
        learn(int(sys.argv[2]) if len(sys.argv) > 2 else 120)
    else:
        decode()
