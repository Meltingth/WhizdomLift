# WhizdomLift

ระบบอ่านสัญญาณตำแหน่งและสถานะลิฟต์ด้วย Arduino Mega 2560 — อ่านหน้าสัมผัสรีเลย์จากตู้ควบคุมลิฟต์ (รหัสตำแหน่ง 6 บิต VS2–VS7 + สถานะ RUNNING / SAFETY / UP / DN / FIRE) ผ่านแผงขั้วต่อ DNMEGA1 และโมดูลรีเลย์ 24V แบบ **read-only ทั้งระบบ** ไม่มีการขับสัญญาณกลับเข้าตู้ลิฟต์

🧭 **เริ่มอ่านที่นี่:** [CLAUDE.md](CLAUDE.md) — บริบทโปรเจกต์ฉบับเต็ม: แผนที่ขาที่ยืนยันแล้ว, สูตรถอดรหัส, กฎความปลอดภัย (**ห้ามตั้งขาเป็น OUTPUT**), บทเรียนจากบั๊กที่เคยให้คำตอบผิด และงานที่ยังเหลือ

🛗 **สถานะลิฟต์ทั้ง 5 ตัว + ขั้นตอนทดสอบ:** [LIFT_STATUS.md](LIFT_STATUS.md) — ลิฟต์ไหนตรวจแล้ว เจออะไร ต้องซ่อมอะไร

📋 **ผลการทดสอบล่าสุด:** [TEST_REPORT_2026-08-08.md](TEST_REPORT_2026-08-08.md) — ยืนยันความแม่นยำด้วย blind test 14/14 เหตุการณ์ พร้อมตารางสอบเทียบรหัส↔ชั้น และ checklist งานที่เหลือร่วมกับทีมดูแลลิฟต์

## โครงสร้าง

| ไฟล์ | หน้าที่ |
|---|---|
| `CLAUDE.md` | บริบทโปรเจกต์ + ข้อเท็จจริงที่ยืนยันแล้ว + บทเรียนจากบั๊ก — โหลดเข้า context อัตโนมัติทุก session |
| `TEST_REPORT_2026-08-08.md` | รายงานผลการทดสอบวันที่ 8 ส.ค. 2026 |
| `IODebug/IODebug.ino` | Sketch บนบอร์ด: อ่าน D2–D53 + A0–A15, watch mode ส่ง `ST <ms> <mask>` ทุกการเปลี่ยนแปลง |
| `LIFT_STATUS.md` | ตารางสถานะลิฟต์ทั้ง 5 + ขั้นตอนทดสอบทีละตัว |
| `log_lift.py` | ตัวบันทึกถาวรต่อลิฟต์: `python log_lift.py COM3 A` — reconnect อัตโนมัติ, heartbeat 60 วิ, กันข้อมูลลิฟต์ปนกัน |
| `lift_health.py` | ตรวจสุขภาพลิฟต์เทียบลิฟต์ A: `python lift_health.py C` — ชี้เส้นที่ไม่ส่งสัญญาณ |
| `lift_decode.py` | Config กลาง: แผนที่ขา→บิตของแต่ละลิฟต์ + ตารางแปลงรหัส→ป้ายชั้น |
| `analyze_lift.py` | ถอดแผนที่บิตอัตโนมัติจากพฤติกรรมสัญญาณ + ไทม์ไลน์ชั้น |
| `trips.py` | แยกเที่ยววิ่ง จุดจอด จุดแวะรับ + จำแนกสัญญาณสถานะ |
| `compare_lifts.py` | เทียบ wiring และรหัสระหว่างลิฟต์หลายตัว |
| `audit.py` / `reveal.py` / `probe_pin.py` | ตรวจข้อมูลดิบ, ตรวจคำตอบ blind test, ทดสอบขาแบบสด |
| `monitor.py` / `scan_pins.py` / `selftest.py` | เครื่องมือ serial monitor, สแกนหาขาที่ต่อจริง, ทดสอบบอร์ด |
| `capture_lift*.log` | ข้อมูลดิบจากการทดสอบ 8 ส.ค. 2026 (ลิฟต์ A + B) |

## เริ่มใช้งาน

```
# อัปโหลด sketch (ครั้งแรกต่อบอร์ด)
arduino-cli compile --fqbn arduino:avr:mega:cpu=atmega2560 IODebug
arduino-cli upload -p COM3 --fqbn arduino:avr:mega:cpu=atmega2560 IODebug

# เริ่มเก็บข้อมูล — ระบุชื่อลิฟต์เสมอ (หนึ่งโปรเซสต่อลิฟต์)
python log_lift.py COM3 A
python log_lift.py COM5 B

# หยุดทุกตัว: สร้างไฟล์ STOP_CAPTURE ในโฟลเดอร์นี้

# ตรวจสุขภาพ + วิเคราะห์
python lift_health.py A
python trips.py
python compare_lifts.py
```
