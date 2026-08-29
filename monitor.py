"""Serial monitor for the IODebug sketch.

    python monitor.py                 capture 20 s and exit
    python monitor.py 60              capture 60 s
    python monitor.py 20 s            capture 20 s, asking for a snapshot first
    python monitor.py 0               run until Ctrl-C

Commands understood by the sketch: h help, s snapshot, r reset stats,
d toggle digital, a toggle analog.
"""
import sys
import time

import serial

PORT = "COM3"
BAUD = 115200

seconds = float(sys.argv[1]) if len(sys.argv) > 1 else 20.0
command = sys.argv[2] if len(sys.argv) > 2 else None

ser = serial.Serial(PORT, BAUD, timeout=0.2)

# Pulse DTR so the sketch restarts and we catch its banner from line one.
ser.dtr = False
ser.rts = False
time.sleep(0.15)
ser.dtr = True
ser.rts = True
time.sleep(0.05)
ser.reset_input_buffer()

if command:
    time.sleep(2.0)                 # let setup() finish before talking to it
    ser.write(command.encode())
    ser.flush()

start = time.time()
buf = b""
try:
    while seconds == 0 or time.time() - start < seconds:
        chunk = ser.read(4096)
        if not chunk:
            continue
        buf += chunk
        while b"\n" in buf:
            line, buf = buf.split(b"\n", 1)
            print(f"[{time.time() - start:6.2f}s] "
                  f"{line.decode('utf-8', 'replace').rstrip()}")
            sys.stdout.flush()
except KeyboardInterrupt:
    print("\nstopped")
finally:
    ser.close()

print(f"\n--- captured {time.time() - start:.1f}s from {PORT} ---")
