"""
Arduino Mega 2560 connection self-test - run this yourself, at your own pace.

    python selftest.py

Every step waits for you to press Enter, and prints its result immediately, so
nothing depends on getting the timing right.

Three questions get answered, in order:
  1. Is the COM port actually this board?      (unplug / replug)
  2. Does the bootloader answer a reset?       (you press RESET)
  3. Does the serial path reach the header?    (D0-D1 jumper)
"""
import sys
import time

import serial
from serial.tools import list_ports

BAUD = 115200
results = {}


# ------------------------------------------------------------------ utils

def hr(title=""):
    print("\n" + "=" * 62)
    if title:
        print(f" {title}")
        print("=" * 62)


def ask(prompt):
    try:
        return input(f"\n>>> {prompt} ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\naborted")
        sys.exit(1)


def ports():
    return {p.device: p.description for p in list_ports.comports()}


def stk2(seq, body):
    head = bytes([0x1B, seq, (len(body) >> 8) & 0xFF, len(body) & 0xFF, 0x0E])
    pkt = head + bytes(body)
    c = 0
    for b in pkt:
        c ^= b
    return pkt + bytes([c])


SIGN_ON_V2 = stk2(1, [0x01])
SYNC_V1 = bytes([0x30, 0x20])


# ------------------------------------------------------- 0. choose a port

hr("Arduino Mega 2560 self-test")
found = ports()
if not found:
    print("No serial ports found at all. Plug the board in and rerun.")
    sys.exit(1)

print("\nSerial ports right now:")
for dev, desc in found.items():
    print(f"   {dev:<6} {desc}")

port = list(found)[0] if len(found) == 1 else None
if port:
    print(f"\nUsing {port}")
else:
    port = ask("Which port? (e.g. COM3)").upper()


# --------------------------------------------- 1. is this port the board?

hr("TEST 1 of 3 - is this port really the board?")
print("If unplugging the board makes this port vanish, the port is the board.")
print("If the port stays, it belongs to some other USB-serial device and the")
print("Arduino is not the thing we have been talking to this whole time.")

ask(f"UNPLUG the USB cable now, then press Enter.")

gone = False
for _ in range(20):                       # up to ~10 s for Windows to notice
    if port not in ports():
        gone = True
        break
    time.sleep(0.5)

if gone:
    print(f"  OK   {port} disappeared -> it IS this board.")
    results["identity"] = True
else:
    print(f"  BAD  {port} is still listed with the cable unplugged.")
    print(f"       {port} is a DIFFERENT USB-serial device, not your Mega.")
    results["identity"] = False

ask("Plug the cable back in, wait for the Windows chime, then press Enter.")

back = False
for _ in range(30):
    if port in ports():
        back = True
        break
    time.sleep(0.5)
print(f"  {port} is back" if back else f"  {port} did not come back - try another USB port")


# ----------------------------------------------- 2. bootloader via RESET

hr("TEST 2 of 3 - does the bootloader answer?")
print("The board's auto-reset does not appear to work, so we reset it by hand.")
print("This listens continuously - press RESET whenever you like.")
print("Take the D0-D1 jumper OUT for this test if you have one fitted.")

results["bootloader"] = False
while True:
    ask("Ready? Press Enter, then tap the RESET button a few times.")
    try:
        ser = serial.Serial(port, BAUD, timeout=0.05)
    except serial.SerialException as e:
        print(f"  cannot open {port}: {e}")
        break
    ser.dtr = False               # never auto-reset; your finger does it
    ser.rts = False
    time.sleep(0.2)
    ser.reset_input_buffer()

    print("\n  listening 30 s - press RESET now")
    end = time.time() + 30
    seen = bytearray()
    hit = None
    while time.time() < end and not hit:
        for probe, tag in ((SIGN_ON_V2, "STK500v2 (Mega)"), (SYNC_V1, "STK500v1 (Uno)")):
            ser.write(probe)
            ser.flush()
            time.sleep(0.06)
            if ser.in_waiting:
                data = ser.read(ser.in_waiting)
                seen += data
                if (tag.startswith("STK500v2") and data[:1] == b"\x1b") or \
                   (tag.startswith("STK500v1") and data[:1] == b"\x14"):
                    hit = tag
                    break
        left = int(end - time.time())
        print(f"\r  {left:2d}s left   bytes received: {len(seen)}   ", end="", flush=True)
    ser.close()
    print()

    if hit:
        print(f"\n  FOUND: {hit} bootloader responded!")
        results["bootloader"] = True
        break
    if seen:
        print(f"\n  Got {len(seen)} bytes but no valid bootloader reply:")
        print(f"    {bytes(seen[:60]).hex(' ')}")
        print(f"    {''.join(chr(b) if 32 <= b < 127 else '.' for b in seen[:60])}")
        print("  Something IS alive on the line - likely a sketch, not a bootloader.")
        results["bootloader"] = "partial"
        break
    print("\n  Nothing received.")
    if ask("Try again? (y/n)") != "y":
        break


# ------------------------------------------------------- 3. loopback path

hr("TEST 3 of 3 - does the serial path reach the pin header?")
print("A jumper from D0 to D1 sends our own bytes straight back to us,")
print("bypassing the ATmega2560 completely.")
print("\nNote: if the MCU is alive and holding TX idle-high, it can block this")
print("test even on a perfectly good board - so a failure here is a hint,")
print("not a verdict.")

if ask("Fit a jumper between D0 and D1 (NOT 5V/GND!), then press Enter, or 's' to skip") == "s":
    results["loopback"] = "skipped"
else:
    pattern = b"LOOPBACK_0123456789\n"
    try:
        ser = serial.Serial(port, BAUD, timeout=0.3)
        ser.dtr = False
        ser.rts = False
        time.sleep(0.2)
        ok = 0
        for i in range(10):
            ser.reset_input_buffer()
            ser.write(pattern)
            ser.flush()
            time.sleep(0.25)
            got = ser.read(ser.in_waiting or 1)
            if pattern.strip() in got:
                ok += 1
            print(f"\r  attempt {i + 1}/10   echoes: {ok}   ", end="", flush=True)
        ser.close()
        print()
        results["loopback"] = ok > 0
        print(f"\n  {'ECHO WORKS - wiring to the header is good' if ok else 'no echo'}")
    except serial.SerialException as e:
        print(f"  error: {e}")
        results["loopback"] = False


# ------------------------------------------------------------- verdict

hr("VERDICT")
ident = results.get("identity")
boot = results.get("bootloader")
loop = results.get("loopback")

print(f"  port is this board : {ident}")
print(f"  bootloader answers : {boot}")
print(f"  loopback echo      : {loop}")
print()

if ident is False:
    print("  -> The COM port is NOT your Arduino. Find the port that disappears")
    print("     when you unplug the board; if none does, the board is not")
    print("     enumerating at all (bad cable, or a dead USB-serial chip).")
elif boot is True:
    print("  -> Board is healthy. Upload with a manual reset: start the upload,")
    print("     then tap RESET the moment it says 'Uploading'.")
elif boot == "partial":
    print("  -> Something is running but no bootloader. A sketch is probably")
    print("     installed with no bootloader behind it - needs an ISP programmer")
    print("     to reflash the bootloader.")
elif loop is True:
    print("  -> Serial wiring is fine but the MCU never answers: the bootloader")
    print("     is missing or the ATmega2560 is not running. Burn a bootloader")
    print("     with an ISP programmer (USBasp, or a second Arduino as ISP).")
else:
    print("  -> Nothing answers on any path. Try a different USB cable first")
    print("     (charge-only cables enumerate but move no data), then a")
    print("     different USB port, then a different board if you have one.")

print("\nCopy this whole output back into the chat and I will take it from there.")
