"""
Guard against shipping a stale firmware image.

    python check_firmware_hex.py

The tracked IODebug.ino.hex is there so a replacement board can be flashed with
avrdude alone, no toolchain. It went stale without anyone noticing: plain
`arduino-cli compile` builds into a temporary directory, so the file under
IODebug/build/ only changes when --export-binaries is passed. It sat at the
very first build of the project for weeks - a version that printed EDGE lines
and snapshots during capture, which is bug 6.1 and silently corrupts data.

This compares FW_VERSION in the source against the strings inside the hex, so
the mismatch is caught mechanically rather than by remembering.
"""
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).parent
SRC = HERE / "IODebug" / "IODebug.ino"
HEX = HERE / "IODebug" / "build" / "arduino.avr.mega" / "IODebug.ino.hex"


def flatten(path):
    img, ext = {}, 0
    for line in path.read_text().splitlines():
        if not line.startswith(":"):
            continue
        n, addr, rt = int(line[1:3], 16), int(line[3:7], 16), int(line[7:9], 16)
        data = bytes.fromhex(line[9:9 + n * 2])
        if rt == 0:
            for i, b in enumerate(data):
                img[ext + addr + i] = b
        elif rt == 4:
            ext = int.from_bytes(data, "big") << 16
    return bytes(img.get(i, 0xFF) for i in range(max(img) + 1)) if img else b""


src = SRC.read_text(encoding="utf-8")
version = re.search(r'#define\s+FW_VERSION\s+"([^"]+)"', src)
if not version:
    sys.exit("FW_VERSION not found in the sketch")
version = version.group(1)

if not HEX.exists():
    sys.exit(f"no built hex at {HEX}\n"
             f"  build it with:  arduino-cli compile --fqbn "
             f"arduino:avr:mega:cpu=atmega2560 --export-binaries IODebug")

blob = flatten(HEX)
ok = version.encode() in blob
print(f"  sketch FW_VERSION : {version}")
print(f"  tracked hex       : {len(blob)} bytes")
print(f"  version string in hex: {'yes' if ok else 'NO'}")
if not ok:
    sys.exit("\nSTALE: the tracked hex was not built from this source.\n"
             "  Rebuild with --export-binaries and commit it, or the next\n"
             "  person to flash from it gets an older firmware than they think.")
print("\n  OK - the tracked hex matches the current source")
