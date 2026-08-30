# ขั้นตอนอัปเกรด Firmware

**ทำที่เครื่อง debug หน้าตู้ ผ่าน USB เท่านั้น** — เครื่อง Gateway อัปเกรดไม่ได้
เพราะลิงก์ RS485 เป็นแบบส่งทางเดียว บอร์ดรับข้อมูลไม่ได้

---

## ข้อดีของการต่อแบบส่งทางเดียว: ไม่ต้องถอดอะไรเลย

เพราะ **`RO` ของ MAX485 ไม่ได้ต่อ** จึงไม่มีอะไรชนกับ CH340 ที่ขา D0
⇒ **เสียบ USB เข้าไปแฟลชได้ทันทีโดยไม่ต้องถอดสาย RS485 ออก**
และ Gateway ก็ไม่ต้องหยุดเก็บข้อมูล

## สิ่งที่ Gateway จะเห็นระหว่างอัปเกรด — และทำไมไม่ต้องตกใจ

| ช่วง | Gateway เห็นอะไร |
|---|---|
| ระหว่างอัปโหลด | **บรรทัดเสียเป็นชุด** (`rejected` พุ่ง) เพราะ bootloader ส่ง STK500v2 ออก TX0 ซึ่งวิ่งออก RS485 ไปด้วย |
| บอร์ดรีบูต | `--- board restarted (clock ... -> ...) ---` |
| บอร์ดพร้อม | `--- FW IODebug <version> <date> ---` ← **ยืนยันว่าเวอร์ชันใหม่ขึ้นแล้ว** |

**แจ้ง Gateway ก่อนอัปเกรดทุกครั้ง** ไม่งั้นคนเฝ้าจะเห็น reject พุ่งแล้วนึกว่าสายมีปัญหา

## ขั้นตอน

### 1. เตรียม toolchain

```
export ARDUINO_DIRECTORIES_DATA=<scratchpad>/tools/data
export ARDUINO_DIRECTORIES_DOWNLOADS=<scratchpad>/tools/dl
export ARDUINO_DIRECTORIES_USER=<scratchpad>/tools/user
```

> scratchpad เป็นพื้นที่ชั่วคราว **ถูกล้างได้** ถ้า `avrdude.conf` หาย ให้ลบโฟลเดอร์
> `data/packages/arduino/tools/avrdude` แล้วสั่ง `arduino-cli core install arduino:avr` ใหม่
> (การสั่ง install เฉย ๆ จะข้าม เพราะเห็นว่าไฟล์ .exe ยังอยู่)

### 2. เพิ่มเลขเวอร์ชันก่อนแก้โค้ดเสมอ

ใน `IODebug/IODebug.ino`:
```c
#define FW_VERSION "1.1.0"
#define FW_DATE    "2026-08-30"
```
**บังคับ** — ถ้าไม่บวกเลข จะไม่มีทางรู้ว่าลิฟต์ตัวไหนได้อัปเดตแล้วบ้าง

### 3. ตรวจความปลอดภัยก่อน compile

```
grep -nE "OUTPUT|digitalWrite|Serial[123]" IODebug/IODebug.ino
```
**ต้องไม่เจออะไรเลย** ถ้าเจอแปลว่ามีโค้ดที่จะขับขาออก หรือเปิด UART ที่ทับสายสัญญาณ

### 4. Compile และ upload

```
arduino-cli compile --fqbn arduino:avr:mega:cpu=atmega2560 --warnings all IODebug
arduino-cli upload -p COM3 --fqbn arduino:avr:mega:cpu=atmega2560 IODebug
```

### 5. ยืนยันว่าขึ้นเวอร์ชันใหม่จริง

```
python -c "
import serial, time
s = serial.Serial('COM3', 115200, timeout=0.2)
time.sleep(4); print(s.read(2000).decode('utf-8','replace'))
s.close()"
```
ต้องเห็น `FW IODebug <เวอร์ชันใหม่>` และมี `ST` ตามมาเองโดยไม่ต้องส่งคำสั่ง

### 6. ตรวจว่ายังอ่านสัญญาณถูก

```
python lift_health.py <lift>
```
ต้องได้ `HEALTHY` และ single-step 100% เหมือนเดิม

### 7. commit + push แล้วแจ้ง Gateway

บอกว่าอัปเกรดลิฟต์ไหนเป็นเวอร์ชันอะไร Gateway จะเห็นบรรทัด `FW` ในล็อกตรงกัน

---

## กฎที่ห้ามละเมิดตอนแก้ firmware

1. **ห้ามตั้งขาใดเป็น `OUTPUT`** — ขาต่อกับหน้าสัมผัสรีเลย์ ขับ HIGH ใส่หน้าสัมผัสที่ปิดอยู่ = พอร์ตพัง
2. **ห้ามพิมพ์อะไรเพิ่มใน watch mode** — บัฟเฟอร์เต็มจะบล็อกลูปสุ่มตัวอย่างและอ่านบิตที่เร็วที่สุดตกหล่น
   เคยทำให้ถอดรหัสผิดทั้งระบบมาแล้ว (`CLAUDE.md` §6.1)
3. **ห้ามเรียก `Serial1.begin()` / `Serial2.begin()`** — ทับ D16/D17/D19 ที่เป็น RUNNING, SAFETY, UP
4. **ห้ามขยับ `DIG_FIRST` / `DIG_LAST`** — ล็อกเก่าทุกไฟล์จะถอดไม่ได้

## ถ้าจำเป็นต้อง rollback

อิมเมจเดิมของแต่ละบอร์ดอยู่ใน `firmware_backup/` (ปัจจุบันมีของ Lift 2 ก่อนเขียนทับ)
**อ่าน flash เก็บไว้ก่อนเขียนทับเสมอ** ถ้าบอร์ดนั้นมีโปรแกรมของทีมอื่นอยู่:

```
avrdude -C <conf> -c wiring -p m2560 -P COM3 -b 115200 \
        -U flash:r:firmware_backup/lift<N>_original.hex:i
```
