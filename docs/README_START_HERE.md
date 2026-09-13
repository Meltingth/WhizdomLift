# LMS-NG Revised Execution Pack v2.0

**สำหรับเจ้าของโครงการและ Claude Code — 13 กันยายน 2026**

ชุดนี้แก้แผนจาก `Pasted text.txt` ให้ดำเนินการได้เป็นเฟส โดยคง 2 เครื่อง / 2 repo / Python Edge และเพิ่มความครบถ้วนของข้อมูล ความปลอดภัยระหว่างย้าย Capture และ HUD ที่มีเกณฑ์รับมอบ

## เริ่มใช้งาน

แตก ZIP ไว้ในโฟลเดอร์เอกสารที่ Claude Code เข้าถึงได้ เช่นโฟลเดอร์ `docs/revisions/` ใน workspace พัฒนา **อย่าแตกทับ source/runtime ของ Capture ที่กำลังทำงาน**. อ่านแผนหลัก แล้วคัดลอกข้อความใน `CLAUDE_CODE_START_PROMPT_TH.txt` ส่งให้ Claude Code พร้อมระบุ path ของโฟลเดอร์นี้

Claude ต้องเริ่ม PRE-0 → A-DRAFT และหยุดที่ G-A. การขอให้ revise ไม่ได้อนุมัติ Contracts bytes หรือการหยุดระบบจริง ในรอบหลังจึงอนุมัติ candidate ที่มี hash และ cutover รายลิฟต์แยกกัน

## ไฟล์สำคัญ

| ไฟล์ | หน้าที่ |
|---|---|
| [แผนหลัก](LMS_NG_Revised_Implementation_Plan_v2_0.md) | ข้อกำหนด A–F, สถาปัตยกรรม, Contracts, Edge, Server, HUD, Canary, Rollback และ DoD |
| [คำสั่งเริ่มงาน](CLAUDE_CODE_START_PROMPT_TH.txt) | ข้อความที่ส่งให้ Claude เพื่อเริ่มลงมือ ไม่ใช่เพียงทบทวนแผนอีกรอบ |
| [ตาราง Phase](PHASES_REVISED.md) | P0–P6 และ subphases ที่ปรับจากลำดับเดิม |
| [Test Matrix](TEST_MATRIX.md) | 77 กรณีทดสอบ พร้อม expected results และก่อน/หลัง Canary |
| [Machine-readable manifest](execution-manifest.json) | dependencies, gates และ test requirements; ไม่ใช่ deploy script |
| templates/ | แบบฟอร์ม workflow state, รายงาน phase, และ cutover approval ที่ยังไม่ได้อนุมัติ |
| reference/ | ต้นฉบับแผน ภาพ HUD และ MQTT/OpenAPI baseline เดิมสำหรับ diff |
| [Sources](SOURCES.md) | แหล่งหลักฐานโครงการและเอกสารเทคนิคที่ใช้ตรวจ semantics |
| PACK_MANIFEST.sha256 | hashes สำหรับตรวจความครบของไฟล์ใน pack |

## จุดสำคัญที่เปลี่ยน

ไม่มี all-lift cutover ใน P1; known-good rollback ไม่พึ่ง code ใหม่; PUBACK ไม่ล้าง durable outbox; ใช้ DB application ACK และ immutable message identity; state ordering ไม่ใช้ wall clock ข้าม boot; TEST/DEMO ไม่ปน REAL; TLS/Auth/backup ก่อน Canary; HUD ต้องมีตู้ลิฟต์เคลื่อนที่/ตัวเลข/quality/Analytics จริง ไม่ใช่แค่การ์ด minimal

Contracts `2.0.0-draft.1` ในแผนเป็น **เวอร์ชัน candidate ที่เสนอให้ Claude สร้าง** ไม่ใช่ release ที่มีอยู่แล้ว. หากตรวจพบเลขชนต้องบันทึกและเลือก candidate ใหม่ ไม่ overwrite tag เดิม. Baseline v1 ใน reference ไม่ใช่ contract ใหม่ที่อนุมัติให้ใช้งาน

ไฟล์ HTML เดิมไม่รวมใน ZIP ให้ส่งต้นฉบับของเจ้าของเพิ่มเมื่อ Claude ต้องอ่าน prototype. ภาพ HUD รวมไว้แล้ว แต่ตัวเลข/อาคารบนภาพไม่ใช่ข้อเท็จจริงหน้างาน

**สถานะ:** เอกสารพร้อมเริ่ม preflight/drafting. ทุก test result = NOT_RUN, ทุก human gate = PENDING. ไม่มีการ deploy หรือทดสอบลิฟต์จริงจากการสร้าง pack นี้
