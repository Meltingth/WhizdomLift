# แหล่งอ้างอิงและขอบเขตหลักฐาน

จัดทำ revision วันที่ 13 กันยายน 2026. ใช้ต้นฉบับของเจ้าของเป็นฐาน และแยกข้อแก้ไขเชิงออกแบบในแผนด้วย [REVISED]/[TARGET]. ไม่ได้เปิดทดสอบ Gateway/Dell หรือยืนยันสถานะ GitHub ใหม่ในรอบจัดทำเอกสารนี้

## เอกสารโครงการ

| ID | เอกสาร | ใช้เพื่อ |
|---|---|---|
| S1 | reference/ORIGINAL_CLAUDE_PLAN_2026-09-13.txt | สถาปัตยกรรม, Deliverable A/B/C, คำตัดสินเจ้าของ, mapping, phase และ guardrails เดิม |
| S2 | reference/legacy-contracts/LMS_NG_MQTT_Topic_Specification_v1.yaml | ตรวจว่ามี contract baseline เดิม; topic root/envelope/session/ACL เป็นข้อมูลสำหรับ diff ไม่ใช่สัญญาใหม่ |
| S3 | reference/legacy-contracts/LMS_NG_OpenAPI_v1.yaml | API baseline, UUID fields, states และ use cases |
| S4 | reference/HUD_VISUAL_REFERENCE.png | ธีม/องค์ประกอบ HUD ที่เจ้าของต้องการ; ตัวเลขในภาพเป็นตัวอย่าง |
| S5 | LMS-NG Live Dashboard.html ของเจ้าของ (ไม่รวมใน ZIP) | Prototype สำหรับอ่าน/แยกส่วนที่นำกลับมาใช้ได้; ไม่อนุมานว่าโค้ดทั้งหมดเป็น LIVE |
| S6 | โค้ด/CLAUDE.md/PHASES/Backend Plan/UXUI ใน repo ที่ค้นพบจริงตอน PRE-0 | สภาพล่าสุดและข้อจำกัดการ deploy; ต้องอ่านจากเครื่อง/สิทธิ์ที่เข้าถึงได้ ไม่ใช่อ้างว่าได้ยืนยันใหม่แล้ว |

ไฟล์ SQL schema/UI enums เดิมยังไม่ได้ใส่สำเนาในชุดนี้ จึงต้องตรวจใน PRE-0; การค้นพบ MQTT/OpenAPI ไม่พิสูจน์ว่าเอกสารอื่นครบ

## เอกสารเทคนิคทางการที่ตรวจอ่านเพื่อปรับแผน

URL อยู่ใน code spans เพื่อคัดลอกไปตรวจตามรุ่นที่ติดตั้งจริง ไม่ใช่ runtime dependency. วันที่ตรวจ 2026-09-13

**T1 — OASIS MQTT 5.0**
`https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html`
ใช้เรื่อง QoS/PUBACK peer acknowledgement, Will ที่กำหนดตอน CONNECT และ retained messages. Application ACK หลัง SQL commit, outbox state machine และ ordering ในแผนเป็นข้อออกแบบเพิ่มเติม ไม่ใช่ฟีเจอร์ที่ MQTT รับรองให้โดยอัตโนมัติ

**T2 — JSON Schema: Objects / Extending closed schemas**
`https://json-schema.org/understanding-json-schema/reference/object`
ใช้ตรวจ additionalProperties เทียบกับ unevaluatedProperties และการประกอบ schema; แผนเลือก nested envelope/payload เพื่อลดความกำกวม

**T3 — PostgreSQL 16: Table Partitioning**
`https://www.postgresql.org/docs/16/ddl-partitioning.html`
ใช้ตรวจข้อจำกัด unique/primary key บน partitioned tables; ingest_receipt แยกเป็นข้อออกแบบของ revision

**T4 — Redis Pub/Sub**
`https://redis.io/docs/latest/develop/pubsub/`
ใช้ยืนยัน Pub/Sub มี at-most-once semantics; server outbox/revision/resnapshot เป็นกลไกที่ต้องเพิ่มเอง

**T5 — OWASP WebSocket Security Cheat Sheet**
`https://cheatsheetseries.owasp.org/cheatsheets/WebSocket_Security_Cheat_Sheet.html`
ใช้ตรวจ authentication, authorization, Origin, session lifecycle, bounded messages และ TLS สำหรับ WebSocket

**T6 — Ajv JSON Schema versions**
`https://ajv.js.org/json-schema.html`
ใช้เลือก validator class/draft ที่ตรง 2020-12 ไม่ถือว่าตัว default รองรับทุก draft

**T6A — MDN requestAnimationFrame**
`https://developer.mozilla.org/en-US/docs/Web/API/Window/requestAnimationFrame`
ใช้แยก callback ก่อน repaint ออกจาก physical pixel-visible time; latency targets เป็นข้อกำหนดทดสอบที่เสนอ ไม่ใช่ผลวัดแล้ว

**T7 — pip Secure installs**
`https://pip.pypa.io/en/stable/topics/secure-installs/`
ใช้เรื่อง pinned dependencies/hash-checking/offline artifacts; ต้องตรวจ binary compatibility ของเครื่องจริงแยก

**T8 — pySerial API**
`https://pyserial.readthedocs.io/en/latest/pyserial_api.html`
ใช้เรื่อง read size/timeout/constructor open และ DTR/RTS caveats. ภาคสนามต้องยืนยันกับ dongle/driver จริง ไม่อ้างว่า options รับประกันไม่มี reset ทุกฮาร์ดแวร์

## ข้อจำกัดของหลักฐาน

- ไม่มีโค้ด Agent/NestJS/HUD production ที่สร้างเสร็จในชุดนี้ เป็น implementation plan และ test specification
- เป้าหมาย latency/FPS/72h buffer/2h Canary/24h soak/120s recovery เป็นค่าเสนอเพื่ออนุมัติและวัด ไม่ใช่ SLA ที่ทดสอบแล้ว
- รายงาน firmware, การซ่อม VS2, drift ของ board และ W-05 mapping มาจาก S1 ไม่ใช่การวัดซ้ำ
- ไม่มีการสร้าง/แก้/push repository, หยุด Capture, เปลี่ยนไฟร์วอลล์ หรือสั่งตู้ลิฟต์จากการจัดทำเอกสารนี้
