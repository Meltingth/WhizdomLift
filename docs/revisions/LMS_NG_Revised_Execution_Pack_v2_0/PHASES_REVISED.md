# PHASES — LMS-NG Whizdom Revised v2.0

ใช้ไฟล์นี้เพื่อ merge/replace เฉพาะตาราง phase ที่ล้าสมัยใน `docs/workflow/PHASES.md` หลังอ่าน repo instructions แล้ว; อย่าเขียนทับบันทึกหน้างาน/หลักฐานรุ่นก่อน. แผนหลักเป็น source of truth: `LMS_NG_Revised_Implementation_Plan_v2_0.md`.

**รอบแรก:** PRE-0 → A-DRAFT → STOP G-A. ไม่มี Live Cutover ใน P1.

| Phase | Repo / เครื่อง | Dependencies / Gates | Scope | Definition of Done |
|---|---|---|---|---|
| PRE-0 | ทั้งสอง / read-only / เครื่องที่เข้าถึงได้ | เริ่มได้ | Inventory + source diff + known-good manifest; ห้ามเปิด port/หยุด Capture | เอกสาร baseline มีหลักฐานและ scope ที่ตรวจจริง; Capture ไม่เปลี่ยน |
| A-DRAFT | lms-ng (+ Edge vendor draft) / เครื่องพัฒนา / scratch DB ที่อนุญาต | PRE-0 | Contracts candidate + schema/examples/OpenAPI/migration draft + baseline diff | Cross-language validation + decision packet/hash; หยุดรอ G-A |
| P0-SERVER | lms-ng / Dell / sandbox | A-DRAFT, G-A | Stack/API skeleton + TLS/ACL/Auth + persistent volumes + backup baseline | Build/migrations/role checks/restore baseline ผ่าน; ไม่มี shared passwords |
| P1-OFFLINE | WhizdomLift / เครื่องพัฒนา | A-DRAFT, G-A | New reader/streaming model/outbox/ACK/replay; no deployed logger refactor | Gateway offline tests ผ่าน; no real serial access |
| P1-SHADOW | WhizdomLift / read-only log reader | P1-OFFLINE, G-A | Tail สำเนา/ไฟล์ที่อนุญาต; TEST IDs only; checkpoint/rotation | ไม่แย่ง COM/ไม่เขียน Capture เดิม; logical states ตรง expected |
| HUD-CORE | lms-ng / browser preview / Dell | P0-SERVER, G-A | Operations shaft + detail + quality/motion + TEST fixtures | UI truthfulness/visual core evidence; ขอ G-U |
| P2-TEST | ทั้งสอง / Dell TEST stack | P0-SERVER, P1-OFFLINE, HUD-CORE, G-A | End-to-end + fault matrix + ordering + realtime resnapshot + latency/FPS | beforeCanary tests ผ่านและหลักฐานพร้อม; ยังไม่หยุด logger จริง |
| P2-CANARY | ทั้งสอง / Gateway + Dell / หนึ่งลิฟต์ | P2-TEST, P1-SHADOW, G-A, G-U, G-C | Authorized one-lift cutover + verification + independent rollback | No collateral Capture disruption; field evidence; หยุดรอ G-R |
| P3-FLEET | ทั้งสอง / หน้างานทีละตัว | P2-CANARY, G-R | ทยอย 1/3/5 ตาม scope; W-04 ไม่ auto-commission | หลักฐานรายลิฟต์/ownership/gaps; ห้ามย้ายทั้งหมดพร้อมกัน |
| P3-HISTORY | lms-ng / TEST / authorized site | P2-TEST, G-A | Event explorer + partitions + mapping-versioned history + Analytics | Counts/coverage/censored intervals/replay recompute ผ่าน |
| P4-ALARMS-DEMO | lms-ng / TEST และ authorized site | P3-HISTORY, G-A | Full Alarm Center + per-session Demo + no contamination | ACK/mute semantics, no historical live notifications, isolated Demo |
| P5-PRESENTATION | lms-ng / browser / Dell | HUD-CORE, P2-TEST, G-A | Presentation HUD + map/background + visual polish | G-U visual review/performance/license evidence |
| P5-DRY-RUN | lms-ng / TEST / presentation | P4-ALARMS-DEMO, G-A | Optional simulated command workflow; REAL LIVE always denied | DRY_RUN result explicit; no serial/hardware dispatch; owner may defer |
| P6-HARDENING | ทั้งสอง / TEST + authorized site | P3-FLEET, P3-HISTORY, P4-ALARMS-DEMO, P5-PRESENTATION, G-R | 24h soak + restore/reconcile + cold boot + security + handover | Field evidence complete; known limitations; ขอ G-H |

## การเปลี่ยนจาก PHASES เดิม

- P1 ไม่รวมแก้ deployed logger, live cutover ทั้ง fleet หรือเปลี่ยน Scheduled Task. ผ่านได้เพียง OFFLINE_READY/SHADOW_READY.
- P2 แยก TEST กับ CANARY; minimum alarms/TLS/Auth/backup/restore/ordering/delivery proof มาก่อน CANARY.
- P3-FLEET เป็นการทยอยรายตัวตาม G-R; P3-HISTORY พัฒนาใน TEST ต่อได้โดยไม่เร่ง cutover.
- HUD-CORE เป็น deliverable จริง ไม่ใช่การ์ดตัวเลขแทนหน้าตามภาพ; Presentation polish ไม่แทน Operations usability.
- P4 Full Alarm/Demo ไม่ใช่จุดเริ่มตรวจ fault; P5 DRY_RUN เป็น optional ตามขอบเขตนำเสนอ ไม่ทำให้ REAL ควบคุมได้.
- P6 เพิ่ม full soak/security/restore/handover; ไม่ใช่เพิ่งทำ protection พื้นฐานครั้งแรก.

## สถานะที่อนุญาต

`NOT_STARTED → IN_PROGRESS → READY_FOR_REVIEW → PASSED` หรือ `BLOCKED/FAILED/DEFERRED_BY_OWNER`. คำว่า PASSED ต้องมีผลทดสอบ ไม่ใช้ commit/push เป็นตัวแทน. Gate approval บันทึกแยกจาก phase status.

## เมื่อเริ่ม session ใหม่

อ่าน WORKFLOW_STATE.json + phase evidence + approvals ล่าสุด; ตรวจ hash/commit ให้ตรง; resume เฉพาะ nextAllowedAction. ห้ามเติม approvedBy หรือ gate token เอง. ถ้ามี code ใหม่หลัง evidence ให้ rerun affected tests ก่อนใช้ผลเก่าเปิด gate.
