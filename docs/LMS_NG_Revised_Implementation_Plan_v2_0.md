---
planId: LMS-NG-WHZ-REVISE-2.0
planVersion: 2.0.0
preparedAt: 2026-09-13
language: th-TH
timezone: Asia/Bangkok
status: READY_FOR_PREFLIGHT_AND_CONTRACT_DRAFTING
contractsApproval: PENDING
liveCutoverApproval: NOT_GRANTED
preparedFor: Claude Code
supersedes: "ลำดับงาน/ข้อกำหนดที่เปลี่ยนอย่างชัดแจ้งจาก Pasted text.txt วันที่ 13 กันยายน 2026"
---

# LMS-NG — Revised Implementation Plan v2.0
## Whizdom POC: Contracts → Sandbox → Shadow/Replay → Realtime HUD → Canary → Rollout

> **คำสั่งสำหรับ Claude Code:** ใช้เอกสารนี้เป็น execution specification ไม่ใช่เพียงข้อเสนอให้สรุปซ้ำ เริ่มจาก PRE-0 และ Deliverable A เท่านั้นในรอบแรก ทำไฟล์และทดสอบที่ไม่กระทบระบบจริง แล้วหยุดที่ Gate G-A เพื่อให้เจ้าของอนุมัติ Contracts ที่สร้างจริง การได้รับเอกสารนี้ไม่ใช่การอนุมัติหยุด Capture, เปิด COM port ที่ใช้งานอยู่, ย้ายลิฟต์ทุกตัว, เปลี่ยน Scheduled Task หรือ deploy ขึ้นหน้างาน

**ผลลัพธ์สุดท้ายที่ต้องได้:** ระบบอ่านอย่างเดียวจาก WhizdomLift แสดงลิฟต์ 5 ตัวใน HUD ที่ตู้ลิฟต์ขยับตามข้อมูลจริง เลขชั้น/สถานะถูกต้อง มีข้อมูลย้อนหลังและ Analytics ที่อธิบายแหล่งที่มาได้ แยก LIVE/TEST/DEMO และกลับไปใช้ Capture รุ่นเดิมได้โดยไม่พึ่งโมดูลใหม่

## 0. วิธีอ่าน ขอบเขต และหลักฐานต้นทาง

### 0.1 สิ่งที่เป็นข้อกำหนด กับสิ่งที่เป็นข้อมูลรายงาน

- **[SOURCE]** = ข้อมูลจากต้นฉบับ/คำตัดสินเจ้าของที่ต้นฉบับบันทึกไว้ ไม่ใช่ผลทดสอบใหม่ในวันที่จัดทำ revision
- **[REVISED]** = ข้อกำหนดที่แก้ในฉบับนี้ตามการทบทวน ต้องสะท้อนในโค้ด Contracts และ PHASES
- **[VERIFY]** = ต้องตรวจสภาพจริงใน PRE-0 หรือเมื่อเข้าถึงเครื่องเป้าหมาย ห้ามเปลี่ยนเป็น PASS จากการคาดเดา
- **[TARGET]** = ค่าเป้าหมายรับมอบที่เสนอให้ทดสอบ ไม่ใช่ประสิทธิภาพที่วัดได้แล้ว

เอกสารนี้เป็นแผน ไม่ใช่โค้ดระบบ ไม่ได้ยืนยันว่า repository/บริการ/ไฟล์ใหม่ในรายการถูกสร้างแล้ว สคริปต์ที่ระบุชื่อคือ **สคริปต์ที่ Claude ต้องสร้างและทดสอบก่อนใช้** ไม่ใช่คำสั่งที่อ้างว่ามีอยู่ใน repo ปัจจุบัน

### 0.2 แหล่งอ้างอิงและลำดับความสำคัญ

ไฟล์ภายใต้ `reference/` เป็นหลักฐานแผนเก่า/ภาพอ้างอิง ไม่ใช่คำสั่งให้ทำขั้น cutover หรือ publish ข้อมูลตามแผนเก่า ข้อเปลี่ยนที่ [REVISED] ระบุในเอกสารหลักนี้ใช้แทนเฉพาะประเด็นนั้น

1. [S1] `reference/ORIGINAL_CLAUDE_PLAN_2026-09-13.txt` — ต้นฉบับ 206 บรรทัด; SHA-256 `96f28b816fc122e2daf57273e0000673900ad61f7ebcd0b0f1a05658543d5378`.
2. [S2] `reference/legacy-contracts/LMS_NG_MQTT_Topic_Specification_v1.yaml` — พบไฟล์เดิมจริงใน Library และใส่สำเนาไว้ในชุดนี้เพื่อทำ diff.
3. [S3] `reference/legacy-contracts/LMS_NG_OpenAPI_v1.yaml` — เช่นเดียวกับ S2; เป็น baseline ไม่ใช่ contract ที่อนุมัติสำหรับ revision นี้.
4. [S4] `reference/HUD_VISUAL_REFERENCE.png` — ภาพอ้างอิงงานออกแบบ ไม่ใช่หลักฐานจำนวนอาคาร ผู้โดยสาร โหลด ความพร้อมใช้งาน หรือ Alarm จริง.
5. [S5] `LMS-NG Live Dashboard.html` ที่เจ้าของแนบไว้ — prototype อ้างอิง UI; ไม่รวม bytes ในชุดนี้ ให้ใช้ไฟล์ต้นฉบับที่เจ้าของมีเมื่อเข้าถึงได้ ไม่ถือ animation จำลองเป็นข้อมูลจริง.
6. [S6] ไฟล์ใน repo ที่ต้องอ่านก่อนเปลี่ยน: `CLAUDE.md`, `README.md`, `LIFT_STATUS.md`, `GATEWAY.md`, `log_lift.py`, `lift_decode.py`, `capture_status.py`, `port_resolver.py` ถ้ามี, `scripts/start_captures.ps1`, `docs/workflow/PHASES.md`, Backend Plan v1.3 และ UX/UI Spec ที่ค้นพบจริง.
7. [T1]–[T8] (รวม T6A) เอกสารเทคนิคทางการอยู่ใน `SOURCES.md`; ใช้ยืนยัน semantics ไม่ใช้แทนข้อมูลหน้างาน.

เมื่อสภาพ repo ใหม่กว่าต้นฉบับ ให้บันทึก diff และผลต่อแผน ไม่เขียนทับหลักฐานเดิม หากขัดกับการยืนยันของเจ้าของ เช่น W-05 code 47 ให้หยุดเฉพาะการเปลี่ยน mapping นั้นและขออนุมัติข้อขัดแย้ง ห้ามเลือกสิ่งที่ทำให้หน้าจอดูสมบูรณ์กว่าโดยไม่มีหลักฐาน

### 0.3 สภาพโครงการที่ใช้ตั้งต้น [SOURCE: S1 Context / Decisions]

| รายการ | ตั้งต้นจากแผนเดิม | วิธีปฏิบัติใน revision |
|---|---|---|
| Gateway | Windows, `GW-WHZ-01`, รายงาน RAM ประมาณ 7.8 GB | ห้ามรัน Server stack/Docker build หนักบนเครื่องนี้ ตรวจจริงก่อนทำงาน |
| Server | Dell `LMS-SRV`, Windows + Docker Desktop/WSL2 ตามแผน | เตรียมโค้ดได้จากเครื่องพัฒนา แต่รัน stack บน Dell/sandbox ที่อนุมัติ |
| Edge | Arduino ต่อ RS485 ทางเดียว, Python Capture | คง read-only; ไม่แก้ firmware ในขอบเขตนี้ |
| ลิฟต์ที่รายงานว่าพร้อม | 1/2/3/5 firmware 1.2.2 + `LIFT=n` | ต้องตรวจจาก Capture/beacon ปัจจุบัน ไม่ยึด COM เก่า |
| Lift 1 | VS2 ซ่อมแล้ว | ข้อมูลใหม่ใช้ mapping ที่ยืนยัน; ประวัติก่อนซ่อมแยก calibration epoch |
| Lift 4 | out of service | ไม่เท่ากับรอติดตั้ง; แยก service / commissioning / telemetry |
| W-05 | `1→B1`, `2→1`, `47→44`; `3..46` ยังไม่สอบเทียบ | คงการตัดสินใจนี้; ห้ามใช้สูตรของ passenger กับช่วงกลาง |
| สัญญาณจริง | position + RUNNING/SAFETY/UP/DN; ไม่มี door | ไม่สร้าง door/occupancy/load/wait-time เป็นค่าจริง |
| FIRE/FIRE RETURN | ยังไม่ผ่าน activation test | capability = ไม่พร้อมใช้งาน; ห้ามแปล missing เป็น false/NORMAL |
| board clock | มี wrap และรายงาน drift ~0.78% | ถือ drift เป็นผลเก่าที่ต้องตรวจ; ไม่ hardcode ชดเชยทุกบอร์ด |
| Repo `lms-ng` | ต้นฉบับระบุว่ายังไม่มี | ตรวจ local/remote จริง; 404 ไม่พิสูจน์ว่าไม่มีหรือ public/private |

คำว่า Contracts “ไม่มีอยู่ที่ไหนเลย” ใน S1 ถูกแทนที่ด้วย: **พบ MQTT/OpenAPI baseline ในชุดนี้แล้ว; PostgreSQL schema/UI enums ให้ตรวจต่อและรายงานเฉพาะขอบเขตที่ค้นจริง**

## 1. การตัดสินใจใน Revision และสิ่งที่ไม่เปลี่ยน

### 1.1 โครงสร้างที่คงไว้

`WhizdomLift` เป็น Edge repo; `lms-ng` เป็น Platform monorepo รวม NestJS, Web, Workers, Contracts, database migrations และ infra ของ EMQX/Postgres/Redis ไม่แยก repo ย่อยตามบริการใน POC และไม่ย้ายทั้งหมดมาอยู่ WhizdomLift [SOURCE: S1; REVISED: ไม่บังคับ submodule]

Python เป็นตัวอ่าน/กรอง/ถอดรหัสบิต ฝั่ง Backend เป็นเจ้าของ floor labels ตาม versioned mapping; Web วาดจาก API model เท่านั้น ห้ามเขียน floor formula ซ้ำใน UI และไม่ port เป็น Go เพียงเพื่อให้ตรงต้นไม้โฟลเดอร์เก่า

### 1.2 ข้อเปลี่ยนที่ต้องบังคับ

| ID | เดิม | Revision ที่ต้องทำ |
|---|---|---|
| R01 | เขียน Contracts ใหม่โดยเชื่อว่าไม่มี baseline | inventory + diff S2/S3 + migration/compatibility decision |
| R02 | submodule บังคับ | repo แยก; สัญญาข้อมูล pin release; submodule เป็น optional ภายหลัง |
| R03 | refactor logger แล้วใช้ logger เป็น rollback | เก็บ known-good release อิสระ; ไม่ refactor deployed logger ใน P1 |
| R04 | live cutover 1/2/3/5 พร้อมกัน | Shadow/TEST ก่อน; canary 1 ตัว; อนุมัติขยายรายตัว |
| R05 | Outbox จบที่ PUBACK | Application ACK หลัง DB commit; duplicate ส่ง ACK ซ้ำได้ |
| R06 | reboot แล้วเปลี่ยนตัวตน backlog | บันทึก immutable message + stream sequence; retry ไม่เปลี่ยน identity |
| R07 | คนละ boot เทียบ wall clock | registered producer epoch + durable per-elevator sequence |
| R08 | FIFO backlog บังข้อมูลสด | fresh-state priority lane + bounded fair history lane |
| R09 | retained birth/will สองค่า | retained presence topic เดียว + connection counter/token |
| R10 | schema composition ปิด object ย่อยทุกชั้น | ใช้ envelope ที่มี payload ปิดแบบชัดเจน; ไม่ปิด allOf ขัดกัน |
| R11 | unique event_time+identity แทน dedupe | durable inbox receipt ID แยกจาก partitioned event table |
| R12 | W-04 disabled → รอติดตั้ง | แยก serviceStatus, commissioningStatus, monitoringEnabled |
| R13 | public reads / 1883 จน P6 | Auth, ACL, HTTPS/WSS, MQTT/TLS ก่อนแตะ LIVE |
| R14 | source switch กลางใน Redis | DEMO ต่อ session; REAL ingestion/alarm ไม่หยุด |
| R15 | minimal cards = UI ส่งมอบ | เพิ่ม Deliverable D: Shaft HUD, Motion, Analytics, visual tests |
| R16 | PASS จาก mock/DoD เดิม | ระบุ PASS/FAIL/BLOCKED/NOT_RUN และหลักฐานจริงราย phase |
| R17 | commit/push ทุกอย่างรวม raw logs | commit source ที่ตรวจแล้ว; ข้อมูล operational/secret ไม่เผยแพร่อัตโนมัติ |
| R18 | security/backup/cold boot ไปท้ายสุด | minimum ก่อน canary; P6 เพิ่ม soak/restore/rehearsal |

### 1.3 สิ่งที่อยู่นอกขอบเขต

ไม่ส่งคำสั่งไปยังตู้ลิฟต์ ไม่แก้ขาเป็น OUTPUT ไม่แฟลช firmware ไม่เปิด remote control ไม่ทดสอบ FIRE ด้วยการกระตุ้นเอง ไม่วินิจฉัยว่าลิฟต์ปลอดภัยจาก dry contact เส้นเดียว และไม่อ้าง predictive maintenance/passenger counting หากยังไม่มีข้อมูลรองรับ

P5 เก็บ Command Console **DRY_RUN เท่านั้น** เป็นงานนำเสนอเมื่อ owner ยืนยันความสำคัญ ห้ามโหมด REAL เรียกเส้นทาง LIVE แม้ role=admin; API ตอบ `COMMAND_NOT_SUPPORTED_READ_ONLY`. ผลจำลองใช้ `SIMULATED_SUCCESS`/`DRY_RUN_COMPLETED` ไม่ใช่ `EXECUTED` ที่อาจเข้าใจว่า hardware ทำงานแล้ว

## 2. กฎการดำเนินงานของ Claude Code

### 2.1 สิทธิ์ในการทำงานและจุดหยุด

| Gate | อนุญาตเมื่อใด | ห้ามก่อนอนุมัติ |
|---|---|---|
| PRE-0 | เริ่มได้เมื่อได้รับแผนนี้ | เปลี่ยน service/task/port/firmware; เปิด Docker บน Gateway |
| G-A | owner อนุมัติ Contract release manifest และ hash ที่สร้างจริง | tag APPROVED เอง; live implementation/cutover |
| G-U | owner ตรวจ HUD preview/ข้อแตกต่างจากภาพ | อ้าง visual fidelity ผ่านแล้วโดยไม่มีการตรวจ |
| G-C | owner อนุมัติลิฟต์เป้าหมาย + release + window + rollback | หยุด Capture ตัวใด; เปลี่ยน task/launcher หน้างาน |
| G-R | owner อนุมัติขยายหลังหลักฐาน canary | ย้ายตัวถัดไป/ทั้ง fleet โดยปริยาย |
| G-H | owner รับมอบผลทดสอบหน้างาน | เรียกระบบว่า field accepted/production ready |

**อนุมัติแผน ≠ อนุมัติ Contracts bytes ≠ อนุมัติ live cutover**. `approvedBy/approvedAt` เริ่มเป็น null; เก็บหลักฐานข้อความอนุมัติและ scope ห้ามเติมชื่อ/เวลาขึ้นเอง ห้ามใช้ environment flag หรือการแก้ JSON เพื่อสร้างการอนุมัติแทนคน

### 2.2 วิธีทำงานใน repo

อ่าน local instructions ที่เกี่ยวข้องและตรวจ git status ก่อนทุกชุดงาน ใช้ feature branch/worktree ที่ไม่ใช่ deployed working tree; branch ตัวอย่าง `feature/lms-ng-revise-v2`. ห้าม `reset --hard`, force-push, ลบ raw log, merge generated output ทับงานคนอื่น หรือ `git add .` บนเครื่อง Capture

แยก commit ตามชุดงานที่ทดสอบได้ พร้อมรหัส phase/test; push branch ที่อนุญาตเมื่อ secret scan ผ่าน ไม่เปลี่ยน visibility repo และไม่สร้าง remote/public repo โดยไม่มีคำสั่งเจ้าของ หาก remote ไม่พร้อมให้รายงาน `REMOTE_UNAVAILABLE` และทำงาน local ต่อในขอบเขตที่ปลอดภัย

ใช้ parallel subagents ได้เฉพาะไฟล์/งานที่แยก ownership; ห้ามสอง agent แก้ Contracts หรือ migration เดียวพร้อมกัน ใช้ one integrator ตรวจ diff และ tests; ไม่มี subagent ใดมีสิทธิ์เปิด gate หน้างาน

### 2.3 ผลลัพธ์ที่ต้องรายงานท้ายทุก phase

รายงาน `phaseId, machineRole, repoCommit, contractHash, filesChanged, testsRun, PASS/FAIL/BLOCKED/NOT_RUN, evidencePaths, remainingRisks, nextAllowedAction` และสถานะ gate ปัจจุบัน ระบุว่าข้อมูลทดสอบเป็น SIM, recorded log หรือ LIVE จริง

unit test ผ่านไม่เท่ากับ field proof; screenshot ไม่เท่ากับ live telemetry; `/health` 200 ไม่เท่ากับลิฟต์พร้อมใช้งาน; skipped test ไม่เท่ากับ PASS. เก็บ `WORKFLOW_STATE.json` ให้ resume ได้ ไม่เขียนว่าทำงานเบื้องหลังหรือกำลังรอข้อมูลหน้างานเมื่อไม่มี process ที่ผู้ดูแลสั่งรันจริง

## 3. PRE-0 — ตรวจ baseline โดยไม่กระทบ Capture

**Repo:** ทั้งสอง; **เครื่อง:** ที่เข้าถึงได้จริง; **ห้าม:** เปิดพอร์ตใหม่เพื่อสำรวจใน phase นี้

สร้างไฟล์:

```text
lms-ng/docs/preflight/BASELINE_INVENTORY.md
lms-ng/docs/preflight/CONTRACT_BASELINE_DIFF.md
lms-ng/docs/preflight/MACHINE_CAPABILITIES.md
lms-ng/docs/preflight/DATA_CLASSIFICATION.md
lms-ng/docs/preflight/DEPENDENCY_MATRIX.md
lms-ng/docs/adr/ADR-001-edge-platform-repositories.md
WhizdomLift/docs/release/KNOWN_GOOD_CAPTURE_MANIFEST.json
```

1. ตรวจ path จริง/remote/default branch/commit/working tree; ไม่ `git init` ทับ repository ที่มีแล้ว ระบุไฟล์ที่ source plan กล่าวถึงแต่ไม่พบจริง
2. อ่าน log/status/process/launcher log ที่มีอยู่โดยไม่แก้ ไม่เก็บ secrets หรือ raw telemetry ลงรายงาน public ตรวจเวลาแก้ไขและ lift identity ที่ยืนยันได้จากข้อมูลเดิม
3. snapshot known-good Capture: commit, dependency lock, Python executable, service account, args, config, private deployment location และ file hashes; copy ออกจาก mutable repo ไป release directory ที่ไม่ import โค้ดใหม่ (ค่า private path อยู่เฉพาะ manifest หน้างาน)
4. ตรวจ task/service topology จาก read-only export เก็บ task XML/credentials reference ไว้ private ระบุว่า stop หนึ่ง lift ได้อย่างไรโดยไม่แตะตัวอื่น หากทำไม่ได้ตอนนี้ให้ BLOCKED เฉพาะ canary
5. อ่าน S2/S3 จาก pack; ค้น SQL/UI enums ใน path ที่เห็นจริงเท่านั้น ไม่เดาว่ามี/ไม่มีทั่วระบบ ไม่เปิด baseline ใหม่เป็น runtime contract โดยอัตโนมัติ
6. ตรวจ Dell capacity/network/storage/runtime โดยไม่เปลี่ยน hostname/IP/firewall เอง ใช้ชื่อ GW-WHZ-01/LMS-SRV เป็น logical role; ยืนยันเครื่องจากหลายหลักฐาน ไม่เชื่อ hostname เพียงอย่างเดียว
7. `Node 22/NestJS 11/pnpm 10/EMQX 5/Postgres 16/Redis 7` เป็น **version targets จากต้นฉบับ ไม่ใช่การยืนยัน latest/supported วันนี้** ตรวจ release/support/license/security compatibility จากเอกสารทางการแล้ว pin exact package versions/image digests; ห้ามติดตั้งรุ่นล่าสุดบน Gateway อัตโนมัติ
8. ประมาณ message rate และ bytes/record จาก log ที่ได้รับอนุญาต ใช้สร้าง queue/storage retention calculation; ห้ามอ่านไฟล์หลาย GB เข้าหน่วยความจำพร้อมกันบน Gateway

**PRE-0 DoD:** inventory ครบเท่าที่เข้าถึงได้, known-good ระบุได้จริงหรือ BLOCKED, baseline MQTT/OpenAPI ไม่ถูกมองข้าม, repo ไม่เสียงาน, Capture ไม่ถูกหยุด และรายงานข้อที่ต้องตรวจหน้างานอย่างตรงไปตรงมา

## 4. Deliverable A — Contracts ฉบับปรับปรุงและ Gate G-A

### A.0 เวอร์ชันและ compatibility [REVISED]

สร้าง **candidate release `2.0.0-draft.1`**, wire `schemaVersion: "2.0"`, MQTT namespace `v2`, WS envelope `v:2`. หมายเลขนี้ตั้งใจแยกจาก v1 baseline ที่เปลี่ยนแบบ breaking ไม่ใช่อ้างว่า v2 มีอยู่แล้ว หาก inventory พบเลขชน ให้เลือกเลขถัดไปและบันทึก ADR ก่อนสร้าง candidate

REST คง base `/api/v1` ได้เฉพาะเมื่อไม่มี deployed consumer ที่เข้ากันไม่ได้; เมื่อพบ consumer ให้เก็บ legacy adapter หรือเปิด REST major ใหม่ โดยสรุปผลก่อน G-A ห้ามตีความ MQTT major = REST major โดยอัตโนมัติ

`CONTRACT_BASELINE_DIFF.md` ต้องเทียบ topic root, envelope/payload, UUID/display code, enums, ACK, LWT, floor owner, simulation, authentication, WebSocket และ retention ระบุ KEEP/CHANGE/REMOVE พร้อมเหตุผล/impact/test. S2/S3 เป็น read-only references ไม่ใช่แฟ้มให้ rewrite

### A.1 ไฟล์ที่ต้องส่งมอบ

```text
lms-ng/contracts/VERSION
lms-ng/contracts/RELEASE_MANIFEST.json
lms-ng/contracts/README.md
lms-ng/contracts/CHANGELOG.md
lms-ng/contracts/mqtt/LMS_NG_MQTT_Topic_Specification_v2.yaml
lms-ng/contracts/mqtt/examples/*.json
lms-ng/contracts/json-schema/common/{ids,enums,time,telemetry-record}.schema.json
lms-ng/contracts/json-schema/mqtt/{state,event,snapshot,presence,heartbeat,diagnostics,ack}.schema.json
lms-ng/contracts/json-schema/ws/{messages,subscriptions}.schema.json
lms-ng/contracts/openapi/LMS_NG_OpenAPI.yaml
lms-ng/contracts/enums/ui-enums.yaml
lms-ng/contracts/fixtures/{valid,invalid}/
lms-ng/database/migrations/<next_number>_*.sql
lms-ng/database/seeds/{whz,test}.sql
lms-ng/packages/contracts/                  # generated/re-exported; ไม่ใช่ schema ต้นฉบับอีกชุด
lms-ng/scripts/{contracts-hash,validate-contracts}.ps1
WhizdomLift/scripts/sync-contracts.ps1
WhizdomLift/tests/test_contracts.py
```

metadata การอนุมัติอยู่ใน release manifest/Markdown frontmatter; JSON Schema ใช้ `$id/$schema/$comment` หรือ extension ที่ validator ยอมรับ; OpenAPI ใช้ `info`/`x-*`. **ห้ามเติม arbitrary header ลง JSON/YAML มาตรฐานแล้วทำให้ parser ใช้ไม่ได้**

pin contract bundle ด้วย tag+commit+SHA-256 manifest; hash จาก sorted relative paths + bytes ที่ normalize LF อย่างระบุแน่นอน ไม่รวม hash ของ manifest ในตัวเองและไม่รวม `SOURCE.md`. build ต้องใช้ของที่ pin แล้ว ไม่ fetch `main` หรือ schemas ทางอินเทอร์เน็ตขณะรัน

ฝั่ง WhizdomLift ตรวจ bundle กับ **รุ่นที่ pin ของตัวเอง** ไม่ใช่บังคับให้เท่ากับ latest tag ของ lms-ng ทุกครั้ง และไม่ทำ CI วงกลมที่สอง repo ต้องอัปเดตพร้อมกันก่อน repo ใดจะผ่าน

### A.2 Model ตัวตนและ provenance

**Internal IDs:** UUID สำหรับ organization/site/building/gateway/elevator. `siteCode=whz`, `gatewayCode=GW-WHZ-01`, `elevatorCode=W-02` เป็นชื่อแสดงที่คงเดิม แต่ไม่ใช่ globally unique primary key. seed IDs ต้องสร้างครั้งเดียวอย่างคงที่และทดสอบว่า seed ซ้ำไม่เปลี่ยน IDs

**Durable telemetry envelope** ต้องมี:

| Field | ความหมาย/ข้อบังคับ |
|---|---|
| schemaVersion / messageType | `2.0`, `state|event`; ประเภท payload ต้องตรง schema/topic |
| messageId | UUID สร้างครั้งเดียวก่อน durable enqueue; retry bytes เดิม |
| organizationId / siteId / gatewayId | UUID ที่ registered; topic/payload/principal/binding ต้องตรงกัน |
| elevatorId | UUID เมื่อเป็น state หรือ event รายลิฟต์; null เฉพาะ lifecycle ของ Gateway ที่ schema อนุญาต |
| producerId / producerEpoch | ตัวตน installation และ epoch ที่ Backend ลงทะเบียนก่อนใช้ LIVE |
| bootId | UUID ของ process ที่สร้าง record; ใช้วินิจฉัย ไม่ใช้เรียงความใหม่ |
| streamId | UUID/stable identifier ของ stream รายลิฟต์หรือ Gateway lifecycle; source counter ของคนละ stream ห้ามปนกัน |
| streamSeq | decimal string เพิ่มต่อเนื่อง **รายลิฟต์/stream ตลอด producer epoch**, เก็บใน SQLite transaction เดียวกับ record |
| eventTime / observedAt | UTC RFC3339 เวลาที่ Gateway รับ source record; ไม่อ้างเป็นเวลาหน้าสัมผัสเปลี่ยนจริง |
| origin | `LIVE|SIMULATED|IMPORT`; immutable; offline retry ของ LIVE ยังคง LIVE |
| sourceRef | capture session + offset/source record ID + decoderVersion/signalConfigVersion; ใช้ trace/dedupe หลัง crash |
| clockQuality | `SYNCED|UNSYNCED|UNCERTAIN` + measured offset/uncertainty เมื่อทราบ |
| payload | object ของ messageType; ไม่กระจายฟิลด์ body ไปชน envelope |

`streamSeq`, ordering revisions และ counters ที่อาจเกิน JavaScript safe integer ส่งเป็น decimal string; จำกัดค่าใน signed bigint range 1..9223372036854775807; ก่อน overflow ต้อง re-enroll epoch; Node/DB ใช้ BigInt/bigint และ compare เชิงตัวเลข ไม่เปรียบ string แบบ lexical. ถ้าต้องใช้ counter ของ Gateway lifecycle ให้เป็น **อีก stream** ที่ระบุชื่อ ห้ามใช้ช่องว่างจาก counter รวมมาสรุปว่าลิฟต์หนึ่งตัวทำข้อมูลหาย

เวลา timeout/debounce/age บน process ใช้ monotonic clock; wall clock ใช้บันทึก/แสดงเวลาและต้องมีคุณภาพกำกับ เมื่อ replay log วันที่ไม่ชัด ห้ามเดาด้วยกฎย้อนเกิน 12 ชั่วโมงเพียงอย่างเดียว ให้ใช้ session date + board continuity + markers; ambiguous time → `UNCERTAIN` และไม่นำไป certify KPI ตามเวลาจริง

### A.3 MQTT topic และแยก data plane [REVISED]

เลือก MQTT 5 สำหรับ POC นี้ก่อน ไม่อ้าง 3.1.1 compatible จนมี test profile แยก:

```text
REAL root: lms/v2/{organizationId}/{siteId}/{gatewayId}
TEST root: lms-sim/v2/{organizationId}/{testSiteId}/{simGatewayId}
```

| Suffix ใต้ root | QoS | Retain | บทบาท |
|---|---:|---|---|
| `telemetry/elevators/{elevatorId}/state` | 1 | false | durable accepted state + changes[]; ส่งทุก accepted change และ board re-emit |
| `telemetry/elevators/{elevatorId}/snapshot` | 1 | true | สำเนา **ล่าสุดเท่านั้น** ของ state record เดิม; cache hint ไม่ใช่ event log |
| `events/elevators/{elevatorId}` | 1 | false | lifecycle/quality event ที่ไม่ใช่ SIGNAL_CHANGE ซ้ำกับ state.changes |
| `events/gateway` | 1 | false | reboot/process/identity/storage events ที่ durable ได้ |
| `status/presence` | 1 | true | topic เดียวสำหรับ ONLINE/OFFLINE + connection identity |
| `status/heartbeat` | 0 | false | process alive + per-lift ages ทุก 10 s; ไม่เข้า durable replay queue |
| `diagnostics/network` | 0 | false | counters/queue/storage ทุก 60 s; ไม่ใช่หลักฐาน telemetry สด |
| `delivery/acks` | 1 | false | Server → Gateway หลัง durable SQL commit; **ไม่ใช่คำสั่งลิฟต์** |

state record มี `changes[]` เพื่อให้ Backend บันทึก current state กับ derived SIGNAL_CHANGE ใน transaction เดียว IDs ของ derived events deterministic จาก parent messageId + index ห้ามส่ง event ชุดเดียวกันซ้ำอีก topic แล้วนับสองครั้ง

snapshot มี messageId/streamSeq/hash ตรงกับ durable record ต้นฉบับ ส่งหลัง enqueue เสมอ การรับทั้ง state และ snapshot ต้องไม่เกิดแถว/Alarm ซ้ำ **ห้าม retry backlog ผ่าน retained snapshot topic** เพราะจะทับ snapshot ล่าสุดใน Broker; ใช้ durable state/event topics ที่ไม่ retained เท่านั้น

heartbeat/presence/ack ใช้ control-plane schema แยก ไม่บังคับ source eventTime/sequence ที่ไม่มีความหมายให้ LWT. ชื่อ topic ตัวอย่างทั้งหมดต้องใช้ registered TEST IDs หรือ placeholder ที่ไม่ publish ได้โดยไม่ได้ตั้งค่า

### A.4 Presence, reconnect และเวลาแสดง offline

ใช้ `connectionId` UUID และ `connectionSeq` decimal string เพิ่มแบบ durable ใน producer epoch ทุกครั้งที่ connect. LWT ถูกเตรียมเมื่อ connect จึงมี `preparedAt` (ไม่ใช่ occurredAt) และ `reason=LWT`. Backend บันทึกเวลาที่รับ will เอง [T1]

on connect: SUBSCRIBE ACK → รอ SUBACK → publish presence ONLINE → heartbeat ปัจจุบัน → ส่ง snapshot ล่าสุดพร้อมอายุจริง → drain queues แบบ priority/fairness. ไม่เปลี่ยน observedAt ของ snapshot เก่าให้เป็น now

Backend รับ OFFLINE เฉพาะ connection ที่ตรงกับ active connection/epoch; will ของ connection เก่าต้องไม่ล้มสถานะ connection ใหม่. topic เดียวทำให้ retained value ถูกแทนด้วย ONLINE เมื่อ reconnect; startup จาก retained ONLINE ยังเป็น `AWAITING_FRESH_PROOF` จนได้รับ heartbeat ปัจจุบัน ห้ามถือ retained ว่าออนไลน์ทันที

unexpected disconnect ตรวจด้วย current will หรือ heartbeat lease. clean shutdown ส่ง presence OFFLINE reason SHUTDOWN ก่อน DISCONNECT เมื่อทำได้. retain ไม่ใช้เป็นหลักฐานความครบถ้วนของประวัติ

### A.5 ACK, Outbox และ transaction boundary [REVISED — ข้อกำหนดหลัก]

PUBACK ยืนยันการรับตาม MQTT ระหว่าง peer ไม่ได้ยืนยัน SQL commit [T1]. เลือก **application-level per-message ACK** เป็นกลไกหลัก ไม่พึ่งว่ารุ่น EMQX เก็บ session ทนไฟดับได้แค่ไหนเพียงอย่างเดียว

**Gateway state:** `PENDING → TRANSPORT_ACKED → DB_COMMITTED`. PUBACK ปรับได้แค่ TRANSPORT_ACKED; เก็บ record ไว้จนได้รับ application ACK ที่ตรง identity+payloadHash. ACK หาย/ซ้ำ/มาผิดลำดับต้องปลอดภัย

**Backend transaction:**

1. authorize principal/realm/site/gateway/elevator/producer; validate schema/limits/topic; invalid → quarantine/diagnostic ไม่ success ACK
2. เริ่ม transaction; `INSERT telemetry.ingest_receipt(message_id, identity, payload_hash, ...)` ที่มี unique messageId และ unique registered stream tuple `(producerId, producerEpoch, streamId, streamSeq)`
3. ถ้าซ้ำ hash เดิมและ receipt COMMITTED → ไม่สร้างผลธุรกิจซ้ำ; ส่ง ACK ซ้ำหลังตรวจ DB. hash ต่าง → `IDENTITY_PAYLOAD_CONFLICT`, quarantine ไม่ ACK ว่าสำเร็จ
4. สำหรับ record ใหม่: insert raw normalized record/history/derived point events; conditional current-state update; insert transactional realtime/alarm outbox เมื่อมีผลปัจจุบัน; update receipt COMMITTED แล้ว COMMIT
5. ส่ง ACK หลัง COMMIT เท่านั้น; publish/fan-out จาก server outbox หลัง COMMIT. ถ้า process ตายก่อนข้อ 5 Gateway retry และจะได้ ACK จาก receipt เดิม

ACK fields: `ackId, schemaVersion, serverDataEpoch, gatewayId, producerId, producerEpoch, messageId, streamId, streamSeq, payloadHash, result=DB_COMMITTED|ALREADY_COMMITTED, committedAt`. จำกัด publisher ของ ACK เป็น Server principal เท่านั้น และ Gateway ตรวจ receipt ของตน ห้ามยอมให้ simulator/ผู้ใช้เว็บ forged ACK มาล้าง Outbox

NACK `INVALID_SCHEMA|WRONG_BINDING|UNKNOWN_PRODUCER|IDENTITY_PAYLOAD_CONFLICT` ไม่ถือว่าส่งสำเร็จ ให้พักใน dead-letter/quarantine ที่ยัง durable เพื่อไม่วน poison record ขวางรายการอื่น; recovery เปลี่ยน record ต้องสร้าง ID ใหม่พร้อม `supersedesMessageId` ไม่แก้ payload ใต้ ID เก่า

ค่าเริ่มต้นทดสอบ: application ACK timeout 10 s, bounded in-flight 20, retry exponential backoff มี jitter จำกัดสูงสุด 60 s; แยก quota งานสด/งานค้าง เช่น fresh ได้สิทธิก่อนแต่ history ได้อย่างน้อย 20% เมื่อมี backlog และต้องไม่ starve stream ใด ค่าเหล่านี้ [TARGET] ปรับจาก load test พร้อมบันทึก ไม่อ้างว่าเป็นค่าที่เหมาะที่สุดแล้ว

**ขอบเขต durability:** ไม่มีคำรับประกันว่าข้อมูลจากหน้าสัมผัสถึงปลายทางไม่หายทุกกรณี สัญญาณอาจหายก่อนรับ/ก่อน durable write หรือระหว่างไฟดับ/cutover; wire ST เดิมไม่มี application checksum จึงตรวจ 13-hex ได้แต่พิสูจน์ bit integrity ทั้งหมดไม่ได้. ข้อรับรองที่ทดสอบคือ **record ที่ยืนยัน durable แล้วจะ retry ถึง DB โดยไม่ duplicate business effect ภายใน fault/retention envelope ที่กำหนด**

**Queue capacity:** ก่อน canary วัด accepted rate/record size แล้วจัดพื้นที่รองรับ [TARGET] outage 72 ชั่วโมงที่ 2×อัตราเฉลี่ยที่วัด พร้อม burst ที่ทดสอบและ reserve disk อย่างน้อย 20%. การคำนวณต้องแสดงสมมุติฐาน/หน่วย ทั้ง SQLite, raw logs, WAL และ retained ACK archive รวมกัน

Purge เฉพาะ DB_COMMITTED ที่พ้น retention ที่อนุมัติ; ค่าเริ่มต้น archive 7 วันเพื่อช่วย server restore. ห้าม silent drop unacknowledged events. หากเต็มให้หยุดทำข้อมูลว่าครบ ใช้ STORAGE_PRESSURE/DATA_LOSS intervals/counters, พยายามคง raw capture ที่มี reserve และแจ้ง local operator; ถ้า disk ใช้ไม่ได้จริงต้องรายงาน Capture failure ไม่อ้างว่ายังปลอดภัยเพราะ process อยู่

**Server restore:** receipt DB อาจย้อนหลังหลัง restore; เปลี่ยน `serverDataEpoch` ด้วย restore runbook ให้ Gate ผู้ดูแลควบคุม และ resend archived records ในช่วงที่ตกลงเพื่อ reconcile. ถ้าอยู่นอก archive/backup coverage ให้แสดง gap ห้ามอ้าง RPO=0. ทำ reconcile tool ที่ไม่ reset current state ไปย้อนหลัง

### A.6 Ordering และ current state ที่ทน restart

ต่อหนึ่ง elevator มี registered stream `(producerId, producerEpoch, streamId, streamSeq)`. producerEpoch ได้จากการลงทะเบียนผู้ดูแล ไม่ถูกเพิ่มเองเพียงเพราะ process restart. streamSeq เพิ่มข้าม boot และจัดสรรพร้อม Outbox record ใน SQLite transaction. bootId เก็บไว้เป็น metadata

Backend อัปเดต current ได้เมื่อ producer/binding epoch ยัง active และ streamSeq มากกว่าที่รับล่าสุดสำหรับ stream นั้น. **ห้ามใช้ `event_time >= current` เป็นตัวตัดสินต่าง boot**. record จาก retired epoch ลง history ได้เมื่อ authorized แต่ไม่ทับ current. ห้ามเปิด writer สองตัวถือ epoch เดียวกัน; enrollment/lease/conflict test ต้องตรวจด้วย

SQLite หาย/restore เก่าจน counter อาจซ้ำ → stop claiming current ownership, report `PRODUCER_STATE_LOST` แล้วให้ผู้ดูแล re-enroll epoch ใหม่ตาม runbook; ไม่เริ่ม seq=1 ใต้ identity เดิม. producer ที่ยังไม่ได้รับอนุมัติ epoch ใหม่อาจเก็บ raw locally แต่ห้ามอัปเดต LIVE current

Backlog สามารถลง history แม้ older; initialization ของ current จากข้อมูลเก่าแสดง `LAST_KNOWN/CATCHING_UP` พร้อมอายุ ไม่สร้างเหตุแจ้งเตือนสดย้อนหลังหรือถือเป็น heartbeat. เฉพาะ state ยืนยันล่าสุดที่ยังสด/คุณภาพผ่านเท่านั้นเข้าสู่ live alarm evaluator; job วิเคราะห์ย้อนหลังเป็นอีก mode

### A.7 State, quality, floor mapping และ identity ของ configuration

state.payload ประกอบด้วย `floorRaw` (string/int ตาม schema เลือกอย่างเดียว; ค่าเสนอ = string), `direction UP|DOWN|IDLE|UNKNOWN`, `motion RUNNING|STOPPED|UNKNOWN`, `statusPoints`, `capabilities`, `raw`, `dataQuality`, `changes[]`, `reemit`.

`SAFETY_DEVICE=true` หมายถึง **หน้าสัมผัสอ่านได้ closed** ไม่ใช่ใบรับรองว่าลิฟต์ปลอดภัย; เพิ่ม `signalMeaning=CONTACT_CLOSED` และข้อความ UI ที่ตรงความหมาย. ค่าที่ไม่ติดตั้ง/ไม่สอบเทียบให้ unknown/null/absent พร้อม capability; `operatingMode=NORMAL|FIRE|UNKNOWN` และ REAL ตั้ง UNKNOWN ถ้ายังไม่มีแหล่งยืนยันโหมด ไม่ derive NORMAL จาก FIRE ที่ missing

เก็บ `signalConfigVersion`, `decoderVersion`, `floorProfileVersion`, `calibrationEvidenceRef`, `effectiveFrom` และช่วง producer/session ที่ใช้ได้. Backend เป็น single owner ของ `floorDisplay`; Edge ไม่คำนวณป้ายชั้น authoritative. CLI readability ใช้ calibration fixture/version ที่ pin ไม่ใช่สร้าง full mapping อีกชุดด้วยมือ

**Passenger profile [SOURCE: S1 A.3]:**

```text
1→B1, 2→1, 3→2, 4→TRANSIT, 5→3, 6→4, 7→5, 8→6,
9→TRANSIT, 10→8, 11→TRANSIT,
12..21 → 9..18, 22..46 → 20..44
```

มี 46 codes/43 landing labels ตรวจ 10 anchors ที่ยืนยันใน repo ด้วย fixture; อย่าสรุปว่าแต่ละค่าถูกจอดทดสอบตรงทั้งหมดหาก evidence เป็นการอนุมานจากประวัติ ให้เก็บ `evidenceType=OPERATOR_CONFIRMED|OBSERVED|INFERRED` ตามหลักฐานจริง

**Service W-05 [SOURCE: คำตัดสินเจ้าของที่ S1 บันทึก]:** `1→B1, 2→1, 47→44`; ช่วง 3–46 = UNCALIBRATED label `code N`. การจอดชั้น 20 ครั้งเดียวปิดได้เฉพาะ anchor นั้น ไม่ถือว่าพิสูจน์ทั้งช่วงอัตโนมัติ ห้ามนำ TRANSIT codes ของ passenger ไปใช้ W-05 โดยไม่มีหลักฐาน

แยก `landingOrder`/`displayAnchor` (ตำแหน่ง schematic ที่สอบเทียบ) จาก `floorDisplay`; profile ที่ไม่ทราบตำแหน่งให้ null และ UI แสดงเส้น raw-code scale แยก ไม่วางตู้ไว้ตรงชั้นอาคารที่เดาเอง. ความสูงต่อชั้นจริงไม่ทราบ → schematic ไม่ใช่เมตรจริง

### A.8 Liveness thresholds และคำจำกัดความ

แยก `lastAnyBytesAt` (diagnostic เท่านั้น), `lastValidFrameAt` (ST หรือ identity ที่รูปแบบ/identity ถูก), `lastValidStateAt` (ST ที่ตรวจรับแล้ว), `lastDecodedAt`, `lastDbAckAt`, browser connection. **ขยะบนสายไม่ทำให้ lift online**; heartbeat ของ Agent ไม่เพิ่ม lastValidStateAt

| ตัวแปร | กฎเสนอที่ไม่เว้นช่องว่าง | เกณฑ์ทดสอบ |
|---|---|---|
| field transport | valid frame age <75s → OK; 75≤age<90 → AGING; ≥90 → NO_RXTX | explicit USB removal อาจแจ้ง DISCONNECTED ทันที; silence ≥90 ถูก flag ไม่เกิน 91s เมื่อ evaluator tick ≤1s |
| source state freshness REAL | valid ST age <90 → within configured validity; ≥90 → STALE | idle 60s re-emit ไม่ false stale; identity อย่างเดียวไม่เติมอายุ ST |
| source freshness SIM | <30s valid; ≥30 stale | ใช้ TEST config แยก |
| Gateway heartbeat | 10s; missed age ≥30 → OFFLINE | ≤31s จาก heartbeat ล่าสุด + UI fan-out ตาม latency budget |
| Broker will | เมื่อรับ will ของ connection ปัจจุบัน | evaluator ≤1s หลังรับ; ไม่อ้างตรวจพบภายใน 1s นับจากสายหลุดจริง |
| UI stream | WS disconnect → SERVER_DISCONNECTED ทันที | หยุด motion/projection; ห้ามรอ source stale90s |

ตัวเลข ≥ ใช้เหมือนกันใน docs/config/code/tests. Render freshness แสดงช่วง AGING โดยไม่ใช้แดงเตือนเพียงเพราะ idle 58s. เหนือสถานะนี้มี `commissioningStatus`, `serviceStatus`, `monitoringEnabled` เป็นแกนอิสระ ไม่สรุปทุกอย่างเป็น connection enum เดียว

ความสดคำนวณโดยใช้เวลาต้นทาง/อายุที่ Agent รายงานจาก monotonic พร้อม confidence และเวลา Server รับ อย่าใช้ receivedAt ใหม่ของ backlog กลบ observedAt เก่า หาก clock ไม่มั่นใจให้แสดง TIME_UNCERTAIN และไม่ certify latency ข้ามเครื่อง

### A.9 PostgreSQL / Redis และ schema migration

ใช้ schemas `core, telemetry, alarm, command, auth, audit` ตามต้นฉบับ เพิ่ม `analytics` เมื่อมี P3. DB เป็น source of truth; Redis cache/pubsub สูญได้แล้ว rebuild/resnapshot ได้ ไม่เป็น event ledger หรือ durable ACK [T4]

Tables ที่ต้องออกแบบและทดสอบ:

| ตาราง | ความรับผิดชอบ |
|---|---|
| core.organization/site/building/gateway/elevator | UUID PK; human code scoped unique; timezone Asia/Bangkok สำหรับแสดง |
| core.producer_registration/gateway_binding | active producer epoch + lift assignment + validity; guard concurrent writer |
| core.floor_profile_version/floor_mapping | immutable version/evidence/effective interval; ห้าม UPDATE ทับประวัติ |
| core.signal_config_version | pin/polarity/debounce/capability version |
| telemetry.ingest_receipt | unpartitioned POC; unique messageId + stream tuple; payload hash/result; เป็น dedupe authority |
| telemetry.records / events | records และ derived events partitioned; eventTime + receivedAt แยก; parent ID + derivation index |
| telemetry.current_state | source sequence + server state revision + mapping version + observed age/quality |
| telemetry.gateway_status / observation_gap | current presence และ known data gaps แบบมีเหตุผล |
| telemetry.realtime_outbox / alarm_input_outbox | enqueue ใน transaction เดียว; retry downstream ได้ |
| alarm.definition/instance/action | separate condition + ACK lifecycle, audit, mute ≠ ACK |
| auth.user/session, audit.log | no shared dev passwords in LIVE; scoped RBAC |
| command.request | P5 dry-run only; migration ไม่ทำให้ REAL write capability เปิด |
| analytics.trip/interval/aggregate | versioned derivation; coverage/censored intervals ไม่ซ่อนข้อมูลขาด |

PG unique บน partitioned tableต้องรวม partition key ตามข้อจำกัด [T3]; จึงอย่าอ้าง `(event_time,...identity)` เป็นการกันซ้ำ global. receipt insert + records/current + server outbox อยู่ใน transaction เดียว; test DB rollback/duplicate/hash mismatch จริง

POC เก็บ receipt ตลอด retention ของประวัติที่ยัง replay/recover ได้; ไม่ prune ที่ 24h โดยไม่ดู edge archive และ imports. เมื่อจะลบ receipt ต้องมี ADR/retention boundary และปฏิเสธ import ที่จะทำ business effect ซ้ำได้

PartitionKeeper มีตั้งแต่ P2: สร้าง current + next2 months และ on-demand historical partitions ภายใต้ lock/privileged migration worker ไม่ให้วันอนาคตผิดปกติสร้าง partitions ไม่จำกัด. FUTURE_TIME/OUT_OF_RANGE เข้าดurable quarantine; ไม่ success ACK ถ้ายังไม่บันทึก durable ตาม policy. ทดสอบข้ามเดือน/ปีและย้อนหลัง

migrations ใช้หมายเลขถัดจากที่มีจริง ไม่แก้ applied migration; fresh DB กับ upgrade DB ต้องผ่าน. `down` ใช้ได้ใน scratch เท่านั้นถ้ามีโอกาสลบข้อมูลจริง ให้ใช้ forward-fix/backup restore ที่อนุมัติ

### A.10 REST / WebSocket contract และ bootstrap

คงรายการ use cases จากต้นฉบับ: auth/me, elevators/status, gateway diagnostics, events, alarms/actions, reports/analytics, Demo start/stop ต่อ session, Commands DRY_RUN. ยังไม่ implement endpoint ให้ตอบ fake success; ที่ยังไม่รองรับให้ระบุใน OpenAPI เป็น planned แยก ไม่อ้างครบ spec

เพิ่ม response model `ElevatorStatus`:

```text
UUID elevatorId + elevatorCode/displayName/siteId
commissioningStatus, serviceStatus, monitoringEnabled
connectionState, transportState, freshness, quality, ageSec
floorRaw, floorDisplay, floorKind, floorProfileVersion, displayAnchor|null
motion, direction, statusPoints, capabilities, operatingMode
sourceObservedAt, serverReceivedAt, serverStateRevision (decimal string)
origin, viewMode (LIVE|TEST|DEMO|HISTORY), producerEpoch
```

WS `wss /ws` authenticated same-origin; server message `{v:2,type,serverInstanceId,datasetEpoch,subscriptionId,viewMode,revision,sentAt,data}`. `snapshot` มี full authorized state; deltas มี per-asset revision ไม่เทียบ eventTime อย่างเดียว. HTTP snapshot กับ WS ต้องมีวิธีปิด race: register subscription/buffer delta ก่อนอ่าน consistent snapshot → ส่ง snapshot พร้อม watermark → ส่ง deltas ที่ revision ใหม่กว่า หรือ resnapshot เมื่อ reconcile ไม่ได้

Redis Pub/Sub เป็น best-effort [T4] จึงต้อง resnapshot เมื่อ redis reconnect, WS reconnect, server instance/dataset epoch เปลี่ยน, revision/checksum mismatch; ส่ง periodic server revision heartbeat และ reconcile snapshot เป็นระยะเพื่อจับ delta สุดท้ายที่หายโดยไม่มี delta ถัดมา. ค่าเสนอ reconcileทุก15s; ไม่ใช้เพื่อเพิ่ม freshness ของ source

slow browser มี bounded buffer; ปิด/ส่ง RESYNC_REQUIRED เมื่อเกิน ไม่เก็บ delta ไม่จำกัด. subscription scope และ session expiry ตรวจบน server; `?siteId` ไม่ใช่สิทธิ์เข้าถึงข้ามไซต์

### A.11 Enums / metadata และ Gate G-A

เพิ่ม `UNKNOWN`, `UNCALIBRATED`, `TRANSIT`, `AGING`, `OUT_OF_SERVICE`, `NOT_COMMISSIONED`, `DATA_QUALITY`, `CAPTURE_OK_DELIVERY_DEGRADED`, `TIME_UNCERTAIN`. เก็บ wording ที่เจ้าของกำหนด: The Whizdom, ศูนย์สัญญาณเตือน, DEMO, DRY RUN, โหมดสาธิต — ข้อมูลจำลองเพื่อการนำเสนอ; คำ รอติดตั้ง ใช้เมื่อยังไม่ติดตั้งจริงเท่านั้น

แยก KPI เช่น `ติดตามข้อมูล 4/5`, `ช่องทางข้อมูลออนไลน์ 4/4`, `งดใช้งาน 1` จาก lift operational availability. `serviceStatus` ที่ยังไม่ยืนยัน = UNKNOWN ไม่อนุมาน IN_SERVICE จาก monitoringEnabled

JSON Schema Draft2020-12: นิยาม envelope root ที่มี payload `$ref` และปิด object ตาม schema นั้นได้; ถ้าต้อง compose allOf ให้ base schemas เปิด แล้วปิดเฉพาะ assembled root ด้วย unevaluatedProperties:false [T2,T6]. Ajv2020 + Python Draft202012Validator/FormatChecker ให้ผลตรงกัน; ไม่ ignore format โดยปริยาย; ตรวจ dynamic status keys ด้วย enum/pattern ที่ระบุ ไม่เปิด arbitrary JSON ทั้ง payload

**G-A packet:** candidate bundle/hash, baseline diff, example valid/invalid, topic ACL matrix, sequence/ACK/presence diagrams แบบข้อความ, database migration test, enum parity, privacy boundaries และ decision log. ทุกไฟล์เริ่ม DRAFT ไม่มี production publish; owner อนุมัติ exact candidate แล้วค่อยออก tag `contracts-v2.0.0` และ vendor ของรุ่นนั้น

## 5. Deliverable B — P1 Gateway Agent โดยไม่รื้อ Capture ที่ deploy อยู่

### B.1 โครงสร้างและ isolation

```text
LIVE mode (เปิดใช้หลัง G-C เท่านั้น)
  Port owner lock + verified LIFT beacon
    → LiftReader → local durable raw journal / legacy-format export
    → StreamingDebouncer → LiftModel
    → SQLite {source cursor + per-lift sequence + immutable outbox}
    → Publisher {fresh lane / history lane} → MQTT
                                           ← application ACK หลัง SQL commit

SHADOW mode
  read-only tail ของ log ที่ logger เดิมเขียน → pipeline เดียวกัน → TEST sink เท่านั้น

REPLAY mode
  copy/fixture ที่ได้รับอนุญาต → deterministic clock → pipeline เดียวกัน → TEST/IMPORT sink
```

คงหนึ่ง logical Gateway และใช้ supervisor + supervised reader workers ตามต้นฉบับได้ แต่ต้องระบุว่า thread isolation ไม่ใช่ process isolation. Publisher/DB retry ห้าม block read loop; เก็บ bounded queue, worker heartbeat, raw journal cursor และ ownership แยกรายลิฟต์ หาก benchmark/kill test พบ reader หนึ่งตัวทำให้คนอื่นหยุด ให้แยก worker เป็น process ผ่าน ADR โดยคง wire contract เดิม ไม่ขยาย microservices ฝั่ง Serverตามไปด้วย

**การขยายรายตัว:** ต้อง hot-add/hot-remove reader ที่ได้รับอนุมัติโดยไม่ restart readers ที่ทำงานแล้ว หรือระบุ blast radius/maintenance approval แยกก่อน restart shared Agent; ห้ามเรียกขั้นที่กระทบตัวอื่นว่า canary isolated

### B.2 สิ่งที่ห้ามเปลี่ยนใน P1

ไม่ทำ `log_lift.py` thin wrapper ใน deployed working tree ไม่สลับ import/dependency ของโปรแกรมเดิม ไม่ overwrite environment/site-packages ที่ service เดิมใช้ ไม่เปลี่ยน default launcher และไม่ใช้ logger ที่ import module ใหม่เป็น rollback

refactor logger เป็นงานภายหลัง G-H หรือแยก PR ที่ระบุเหตุผล/compatibility; ไม่เป็น dependency ที่ทำให้ P1 ต้องเปลี่ยนสิ่งที่ใช้งานดีอยู่ก่อน

### B.3 โมดูลที่ต้องสร้าง/เพิ่ม

| ไฟล์/ส่วน | หน้าที่และข้อจำกัด |
|---|---|
| `agent/lift_reader.py` | parse ST/beacon/restart/wrap + read(1)/bounded in_waiting; ไม่มี serial writes; module ใหม่ไม่ถูก import โดย old logger |
| `agent/port_finder.py` | scan เฉพาะ ports ที่อยู่ใน allowed config และไม่มี owner; single scan coordinator; no COM-based identity |
| `agent/ownership.py` | OS/process lock + per-lift lease file; verify PID + start time + executable + token ไม่ใช้ PID อย่างเดียว |
| `agent/raw_journal.py` | durable record/source offset สำหรับ recover ระหว่าง read/decode/Outbox; rotate ด้วย bounded disk policy |
| `agent/capture_writer.py` | legacy-format export; timestamps ตั้งใจปรับได้ตาม compatibility contract ไม่อ้าง byte-identical ทั้งข้อมูลเวลา |
| `agent/stream_debounce.py` | feed/tick/reset; per-pin hold60ms/composite settle150ms defaults; monotonic timers; quality flags |
| `agent/lift_model.py` | floorRaw/direction/motion/raw contacts; no labels authoritative; sensor suspicion ไม่แก้เลขให้สวย |
| `agent/payloads.py` | bind contract/schema registry offline, one source ของ topic builder/JSON serialization |
| `agent/outbox.py` | durable identity/counters/cursor; ACK states; archive/retry/quarantine/restore reconciliation |
| `agent/mqtt_publisher.py` | TLS, presence, heartbeat, ACK subscriber, fresh/backlog fairness; no hardware command dispatch |
| `agent/replay.py` | log parser dates/markers/uncertainty; absolute separation TEST/IMPORT; deterministic message/run identity |
| `agent/shadow.py` | tail read-only; checkpoint/rotation; remap LIVE IDs เป็น TEST IDs ใน export; preserve private source trace |
| `lms_gateway_agent.py` | CLI entrypoint ที่ไม่ start live จาก default invocation |
| `config/lms_gateway_agent.example.json` | allowlist/profile/topic/auth refs; secrets ไม่อยู่ใน repo |
| `tools/agent_health.py` | Capture/Decode/Delivery/Storage แยก; expected absent/migrating lift ไม่ fail ทั้ง fleet |
| `tools/live_equivalence.py` | compare logical states และเวลาแบบ bounded tolerance ไม่ใช่แค่เทียบ bytes |
| `scripts/canary-*.ps1` | สร้างภายหลัง; default plan-only; ต้องมี gate token และ host/lift/release validation |

**CLI defaults:** `--mode validate|replay|shadow|live`; default `validate`, publisher default `dry-run`; `live` ต้องระบุ config/deployment-manifest/gate-record/lifts ชัดเจน. หาก `--mode replay` กับ REAL credentials/root ให้ fail ก่อนเชื่อมต่อ ไม่อาศัยเพียง UI badge

### B.4 Reader, identity และ bounds

ตรวจ ST แบบ full match, boardMs เป็น uint32, mask 13 hex, max line/buffer length/timeouts; bounded garbage quarantine ป้องกันบัฟเฟอร์โตไม่จำกัด. raw bytes ที่ invalid ไม่นำไปเพิ่ม liveness/ตำแหน่ง

ตั้ง DTR/RTS ก่อน open และใช้ RS485 receive-only path; ไม่อ้างว่าการตั้งค่านี้รับประกันไม่ reset Arduino USB ทุก driver. ห้ามสแกน USB debug board/อุปกรณ์อื่นบนเครื่องโดยปริยาย

LIFT=0/unknown/duplicate → refuse binding + preserve diagnostic ไม่ publish current. Lift 3 ตามต้นฉบับใหม่ไม่ต้อง --map แล้ว; legacy --map มีได้เฉพาะ manual exception ที่ระบุหลักฐาน physical mapping/expiry; COM map อย่างเดียวไม่ป้องกันตัวตนสลับ

ใน canary loggers เดิมถือพอร์ตอื่นอยู่ ให้รายงาน `EXTERNAL_CAPTURE_OWNER` และไม่ scan/open พอร์ตเหล่านั้น. W-04 ตั้ง expected absent แต่หากปรากฏ board ต้องเป็น `DISCOVERED_NOT_COMMISSIONED` ก่อน ไม่ bind แล้วเพิ่ม online KPI อัตโนมัติ

startup หาก source ยังไม่ส่ง ST ให้ `WAITING_SOURCE_BASELINE`; firmware re-emit60s ทำให้ fresh baseline อาจไม่มาทันที ไม่ fabricate initial floor. identity verify acquisition และเวลาพร้อมอ่านแยกจาก steady-state latency ≤2s

### B.5 Streaming debounce และการตรวจสัญญาณ

ใช้ clock source ที่ test inject ได้; sample ใหม่รีเซ็ต per-pin timer, เมื่อ hold ครบจึง accept; composite code ต้องนิ่งครบ settle ก่อน emit. tick ใช้ monotonic PC clock anchored กับเวลารับ ไม่ extrapolate จาก wall clock ที่ NTP เลื่อนได้. หลัง restart/wrap/discontinuity ห้ามสร้าง transitions ข้ามช่วงที่ไม่รู้

เทียบ offline `debounce_pins()` เป็น regression reference เท่านั้น ระบุความต่างของ startup/tail/lookahead เป็น expected deltas มี tests อิสระยืนยันกรณีที่ offline implementation ไม่ใช่ oracle สมบูรณ์. เมื่อ port silent ระหว่าง pending transition ไม่รอ forever; หากยังอยู่ใน receive-valid horizon ให้ settle state ล่าสุดที่ได้รับจริงพร้อม quality, ไม่สรุปว่าตัวแปรอื่น/ตำแหน่งถัดไปเกิดแล้ว

RUNNING=false แต่ floorเปลี่ยนต่อเนื่อง หรือ UP+DN active พร้อมกัน → quality conflict + motion UNKNOWN ตามช่วง debounce ไม่เอา UP ที่ค้างตอนจอดมาใช้สั่งตู้เคลื่อนเอง

VS2 detector thresholds 8/4 ของแผนเดิมใช้ได้เป็น **candidate diagnostic rule** ต้องระบุ inference และทดสอบ false positives กับ input ที่ missing/noisy. ชื่อ default `POSITION_BIT_SUSPECT` ไม่ตั้ง `positionResolution=2` เป็นข้อยืนยันหรือชดเชยเลขชั้นเอง การเปิด specific SENSOR_VS2_FAULT เป็น Alarm ต้องผ่าน calibration/test/owner acknowledgement

### B.6 Durability ของ raw data และ compatible output

raw journal/source cursor ช่วย recover ช่วง raw append สำเร็จแต่ SQLite ยังไม่ enqueue; ต้องกำหนด source ID ที่ recoverซ้ำได้ และ insert cursor+outbox atomically. policy flush/fsync ระบุจำนวน sample หรือ latency budget ที่อาจสูญก่อน durable checkpoint; ห้ามเรียก line-buffered file ว่ารอดไฟดับแน่นอน

Legacy `.log` เป็น compatible export ไม่ใช่ source of truth เดียวที่ไม่มีวันที่/source ID. ข้อมูลใหม่เก็บ date+timezone/session+source sequence ใน sidecar/journal โดยไม่แก้ logเก่า; export เวลาหรือ formatที่เปลี่ยนต้องมี versioned compatibility note

Queue full/disk full/DLL import error/invalid config ต้องมี failure mode ที่สังเกตได้; failure ฝั่งส่งไม่หยุด raw Capture ตราบเท่าที่ยังเขียน disk ได้. full-disk testต้องใช้ bounded scratch volume เท่านั้น ห้ามเติม disk เครื่องจริงจนเต็ม

### B.7 Dependencies และ release package

ใช้ dedicated venv/release runtime ของ Agent; lock exact versions + hashes และ offline wheelhouse ที่เข้ากับ Windows/architecture เป้าหมายตาม policy ไม่ `pip install` ล่าสุดทับ vendor ของ Capture เดิม. ทำ SBOM/license/secret scan ของ release [T7]

Known-good Capture release ต้อง include dependencies/config แยกและทดสอบ import จาก directoryของมันโดยปิด PYTHONPATH ที่ชี้โค้ดใหม่. release artifacts ที่ private ห้าม publish public พร้อม source fixtures

### B.8 B.3 เดิมถูกแทนด้วยขั้นตอนนี้

B-01 freeze baseline/fixtures สำเนาที่ลบข้อมูลอ่อนไหวแล้ว → B-02 new reader/fake ports → B-03 streaming model → B-04 contract builders → B-05 SQLite+ACK+fair retry → B-06 CLI replay/shadow → B-07 status/health → B-08 package release → B-09 TEST integration บน Dell.

**ไม่มี Live Cutover อยู่ใน P1 อีกต่อไป**. Phase P1 สรุป `OFFLINE_READY` หรือ `SHADOW_READY`, ยังไม่ใช่ `LIVE_DONE`. cutover แยกใน Deliverable E หลัง P2-TEST/G-C

## 6. Deliverable C — P0/P2 Server บน Dell

### C.1 Platform monorepo

```text
lms-ng/
├── apps/api/                       # NestJS modular monolith: REST/WS/auth/ingestion/liveness
├── apps/web/                       # Vite + React + TypeScript HUD
├── apps/workers/                   # shared modules; แยก process ตาม fault/throughput ที่ต้องการ
├── packages/contracts/            # types/validators generated จาก contracts ต้นฉบับ
├── packages/ui-kit/               # HUD design tokens/components
├── packages/test-fixtures/         # SIM หรือ redacted fixtures เท่านั้น
├── contracts/
├── database/{migrations,seeds,queries}/
├── infra/{docker-compose,mqtt,postgres,redis,tls,reverse-proxy,backup}/
├── tools/{simulator,replay,load-test}/
├── scripts/
├── tests/{contract,integration,e2e,failure,performance,security}/
├── docs/{preflight,adr,workflow,backend,design,runbooks,evidence}/
└── .github/workflows/
```

ไม่มี `firmware/rs485-gateway` submodule เป็นเงื่อนไข build. simulator/replay harness ใช้ contract fixture/release artifact ที่ pin. WhizdomLift วางข้าง repo ได้เพื่อพัฒนา แต่ pathข้างกันไม่ใช่ runtime dependency

### C.2 P0-SERVER — Sandbox และความปลอดภัยขั้นต่ำ

บน Dell ที่ยืนยัน role/spec แล้ว หรือเครื่อง sandbox ที่เจ้าของอนุญาต: pin EMQX/Postgres/Redis/API/Web/migration images ตาม PRE-0; volume persistent เฉพาะข้อมูลที่จำเป็น; migration one-shot before serviceพร้อม; internal network DB/Redis ไม่ expose LAN; EMQX admin local/VPNเท่านั้น

REAL MQTT ใช้8883 TLSตั้งแต่เริ่มเชื่อมจริง; 1883 อนุญาตได้เฉพาะ isolated test bridge/loopback พร้อม explicit dev profile ห้าม runbook เปิด 1883 บน LAN เพื่อให้ผ่าน testง่ายขึ้น. web443 HTTPS/WSS same-origin; certificate verify hostname/CA; ห้าม `rejectUnauthorized=false`

generate unique credentials outside Git; account/principal แยก REAL gateway, TEST simulator, ingestion server และ viewer. ACL render UUID/topic concrete จาก registry ไม่คัดลอก wildcardตัวอย่างที่ไม่ match topic จริง. API subscribe REAL และ TEST namespaces ที่ได้รับอนุญาต **ทั้งคู่** ใน TEST profile; production consumerของ TEST ปิดหรือแยก deploymentตาม role

default `AUTH_READ_PUBLIC=false`; viewer kioskมี identity read-onlyจำกัดsite. JWT keys/expiry/refresh/revocation ฝั่ง API; WebSocketตรวจsession/origin/subscriptionและปิดเมื่อหมดอายุ. การส่ง cookieต้องมี sameSite/CSRF policyที่ตรงกับ handshake; browser WSไม่รับ arbitrary Authorization headerแบบ fetch จึงเลือก session cookieหรือ short-lived one-use WS ticket ห้ามใส่ long-lived token ใน URL [T5]

`/health/live` ตรวจ process/event loop; `/health/ready` ตรวจสิ่งที่ต้องพร้อมบริการ; `/health/components` authenticatedแยก Capture/DB/MQTT/Redis/jobs. Redisล่มต้องระบุ realtime degradedและ resnapshot ไม่ทำให้ gatewayหยุดCaptureหรือบิดเบือนข้อมูลว่า offlineหมด. metrics admin only/redacted ไม่แสดง secrets

### C.3 Ingestion, state, Alarm outbox และการทำซ้ำ

implement TopicRouter → schema → scope/binding → registered producer → durable transactionใน A.5 → application ACK → server outbox dispatcher. outbox dispatcher polling ต้อง recoverหาก Redis Pub/Subหาย เพราะ Pub/Subไม่ใช่ durable queue [T4]

หนึ่ง state sample สร้าง history+derived changesครั้งเดียว; duplicate receiptไม่ยิง notificationซ้ำ. realtime updateเฉพาะหลัง commitและ monotonic revisionผ่าน; Alarm evaluationรับเฉพาะ eligible current observation/liveness transitions ไม่ใช้ retryมานับ durationเพิ่ม

P2 ยังไม่ต้องมี Alarm Centerเต็ม แต่ต้องมี DATA_QUALITY/STORAGE_PRESSURE/IDENTITY_CONFLICT/GATEWAY_OFFLINE/INTERFACE_NO_RXTX operational diagnostics ที่เห็นบนหน้าจอและlogได้ก่อนcanary

### C.4 Simulator / recorded replay / Demo

Simulatorใช้ registered TEST organization/site/gateway/elevator IDs เช่น display S-01..S-03; refuse target W-* หรือ REAL UUID ก่อน connect. ACL/server authorization enforceซ้ำ แม้ client guardถูกข้ามก็ต้องเขียน REALไม่ได้

recorded replayของไฟล์จริง = HISTORY/TEST input โดย remap IDsและแสดงป้าย `REPLAY` ชัดเจน ถ้าเป็น authorized historical importเข้า productionต้องใช้ IMPORT role/endpoint+jobที่ history-only ไม่มี current/alarm effect. ต่างจาก retryของ LIVE outboxซึ่ง originคง LIVE และยังต้องการACK

DEMO = session overlay/dedicated demo runtime ไม่ publish MQTT และไม่แตะ telemetry/alarm/commandจริง ไม่มี global Redis `lms:source` ที่สลับทั้งอาคาร. ใช้ display aliasesของลิฟต์จริงได้เฉพาะภายใน demo sceneที่ติด DEMO bannerถาวร; domain resource IDsภายในต้องเป็น DEMO IDsที่เขียนเข้าREALไม่ได้

Live ingestion/Alarmของหน้าจอผู้ปฏิบัติงานอื่นเดินต่อเมื่อมีใครDemo. Demo start/stopบันทึก auditจริงได้ (actor/session/time/action) แต่ห้ามบันทึก simulated measurementsเป็นLIVE. metrics ที่ยืนยัน zero contaminationแยกตาราง/namespaceชัดเจน

### C.5 First end-to-end slice

TEST state → DB receipt/history/current → REST+WS snapshot → shaftตู้หนึ่งตัวบน HUD → simulated step/stop/unknown/disconnect → reconnect/resnapshot. ต้องเป็นภาพเคลื่อนไหวที่ขับด้วยข้อมูลสัญญา ไม่ใช่ animation timelineที่ทำขึ้นคู่ขนานให้ดูเหมือนข้อมูลถูกใช้

เมื่อsliceผ่าน ขยายTESTสามตัวแล้วทดสอบปริมาณเทียบห้าลิฟต์/หลาย browser. ถ้าไม่มีDellให้ทำunit/schema/local previewที่ปลอดภัยและระบุ `DELL_TESTS_BLOCKED`; ห้ามใช้Gatewayแทนโดยปริยาย

### C.6 Cold boot / backup baseline ก่อน canary

Docker Desktop/WSL2ที่เริ่มเมื่อloginตามต้นฉบับยังไม่พิสูจน์ unattended service; ทดสอบ rebootจริงในsandboxของDellก่อนอ้างพร้อมNOC. ห้ามเปิด auto-login adminเพื่อแก้ง่าย ๆ โดยไม่ได้ยอมรับความเสี่ยง. เมื่อสภาพOSไม่สามารถทำเป้าหมายนี้ได้ ให้เสนอวิธีhostingที่อนุมัติ (เช่น VM/service host) และ BLOCKED gate; ไม่ย้ายstackไปGateway

P0/P2ต้องมีbackup+restore drillของDB, mappings, registry, secrets recovery refs, Broker config/CA และserverDataEpoch. ก่อน migration/canaryมี snapshotของรุ่นก่อน; backupเก็บencryptedนอกเครื่องหลักตามสิทธิ์. การสำรองข้ามไปGatewayต้องจำกัดI/O/storageไม่แย่งCapture; ค่าเริ่มต้นเลือกoff-host destinationที่ตรวจแล้ว ไม่อ้างว่าคัดลอกไฟล์ข้ามสองPCเพียงอย่างเดียวคือ disaster recoveryครบ

W32Time/NTP/SRV→GWเป็นtargetในต้นฉบับ ให้ตรวจOS/domain policyจริงก่อนตั้งค่า; ไม่แก้registry/time serviceอัตโนมัติ. P95ข้ามเครื่องไม่certifyถ้า clock uncertaintyเกิน200ms หรือBrowserยังไม่ตรวจclock

## 7. Deliverable D — HUD UI, Motion และ Analytics ที่ต้องส่งมอบ

### D.1 ขอบเขต UI ที่ผูกกับความต้องการเจ้าของ

[REVISED จาก minimal C.4] สร้างหน้า **Operations HUD** และ **Presentation HUD** ใช้datasetเดียว ไม่ทำสองBackend

| พื้นที่/องค์ประกอบ | เนื้อหาที่ต้องมี |
|---|---|
| Header | The Whizdom / LMS-NG, เวลาAsia/Bangkok, LIVE/TEST/DEMO, Server/Gateway health |
| KPI bar | ลิฟต์ทั้งหมด, ตัวที่ติดตาม, ช่องทางข้อมูลออนไลน์, motion ที่ทราบ, alarmที่ใช้งานได้; ไม่ใส่ passenger/loadปลอม |
| Shaft overview | W-01..W-05, grid/ชั้นตามprofile, ตู้เคลื่อนที่, เลขชั้น/รหัสดิบ, direction/motion, quality/age |
| Elevator detail | สัญญาณที่มีจริง, firmware/source identity, raw code, calibrated labels/evidence, history, healthแยกชั้น |
| Analytics | จำนวนเที่ยวและเวลาวิ่ง/จอดที่นิยามแล้ว, trip-by-hour, floor visits, coverage; gapsไม่ถูกเติมเป็น0 |
| Events/Alarm | ล่าสุดที่ยืนยันแล้ว, severity icon+text, ACKแยกmute, quality conflicts |
| Presentation map | โลกสีน้ำเงินเรืองแสงและanimated linksตามภาพ; จุดอาคารที่ตั้งค่าจริง; ไม่มีอาคาร/ประเทศปลอมบนLIVE |
| Health footer | Capture, field link, delivery backlog, API/DB/Redis, current data age, เวอร์ชันระบบ |

**ธีม:** dark navy/black, cyan/blue glow, thin cut-corner frames, monospaced numbers, spacingอ่านได้, ภาษาไทยถูกต้อง. glow/scan-line/particlesอยู่backgroundและลดได้; ข้อมูลสำคัญห้ามเป็นภาพrasterหรือข้อความที่ติดในPNG. ไม่ใช้ภาพreferenceทั้งภาพเป็นbackgroundแล้วoverlayเฉพาะตัวเลขเพื่ออ้างว่าได้HUDที่ใช้งานจริงครบ

Operationsให้shaftเป็นพื้นที่หลัก; Presentationให้แผนที่ใหญ่ตามโจทย์ได้ แผนที่เป็นoptional decorative layerซึ่งปิดได้โดยไม่กระทบCapture/monitoring. ไม่ต้องมีThree.js/WebGLเพื่อทำ2D shaft; เริ่มSVG/CSS/Canvasตามประสิทธิภาพที่ทดสอบ แล้วเพิ่ม3Dเมื่อจำเป็นจริง

### D.2 Component / code deliverables

```text
apps/web/src/features/hud/{OperationsHud,PresentationHud}.tsx
apps/web/src/features/elevators/{ShaftOverview,ElevatorCar,FloorScale,ElevatorDetail}.tsx
apps/web/src/features/monitoring/{ConnectionBadge,FreshnessBadge,QualityBadge}.tsx
apps/web/src/features/analytics/{TripsChart,RuntimeChart,DataCoverageCard}.tsx
apps/web/src/features/events/RecentEvents.tsx
apps/web/src/features/demo/{DemoSessionBoundary,DemoBanner}.tsx
apps/web/src/realtime/{client,store,reconciler}.ts
apps/web/src/motion/{positionMapper,motionController}.ts
packages/ui-kit/src/{tokens,hud-frame,numeric-display}/
docs/design/{HUD_SPEC_V2,HUD_ACCEPTANCE,ANALYTICS_DEFINITIONS}.md
```

Reuseองค์ประกอบHTMLเดิมได้เมื่ออ่านsourceและlicenseได้ ไม่ยกroute simulation/data freshnessปลอมเข้าLIVE. assets/fonts/icons/chart librariesต้องมีlicense inventoryและlocal servingเพื่อทำงานบนLANโดยไม่พึ่งCDN. ไม่เผยแพร่ฟอนต์ที่ไม่มีสิทธิ์

### D.3 Motion truthfulness — กฎที่ทดสอบอัตโนมัติ

1. เลขชั้นใช้สถานะconfirmedจากAPIทันที; ตำแหน่งไอคอนใช้visual interpolationไปยังanchorของข้อมูลล่าสุดเท่านั้น ไม่ทำนายปลายทางจากUP/DOWNเอง
2. `motion=UNKNOWN`, sourceinvalid, WS disconnected, fieldlost → หยุดการคาดการณ์/animation loopของตู้ แสดงlast-knownพร้อมอายุ; ไม่ทำให้เคลื่อนต่อเพียงเพราะroute timerเดิมยังทำงาน
3. ความนุ่มนวลเป็นschematic interpolationไม่ใช่encoder positionจริง. ในช่วงข้อมูลใหม่ยังไม่มา ห้ามเลื่อนผ่านชั้นเพิ่มเอง. Alarm/ตัวเลขอัปเดตไม่ต้องรอanimationจบ
4. TRANSITไม่มีfloor landingปลอม; วาดช่วงระหว่างanchorได้เฉพาะprofileกำหนด ถ้าไม่ทราบใช้raw-code track ไม่ใส่เลขชั้นอาคารที่เดา
5. W-05ช่วงuncalibratedแสดง `code N` และเส้นทางschematic raw scaleที่ระบุ ไม่วาดเสมือนขึ้นชั้น44ก่อนได้รับcode47ที่ยืนยัน
6. ปรับtargetกลางanimationจากตำแหน่งที่วาดขณะนั้น ไม่queueทุกtransitionจนจอช้ากว่าข้อมูลหลายวินาที; duplicate/older revisionไม่เริ่มanimationซ้ำ
7. tab background/กลับforeground/resize/reconnect → snap/resyncจากauthoritative state ไม่เล่นย้อนหลังทุกframe
8. `prefers-reduced-motion` และoperator toggleปิดbackgroundanimationได้; ไม่มีcolor-onlyalarm และไม่มีflashที่รบกวนการอ่าน

### D.4 นิยาม Analytics ระยะเริ่มต้น [TARGET / เสนอให้อนุมัติ G-A]

- **Trip:** เริ่มเมื่อ RUNNINGยืนยันและมีvalid position progression; จบเมื่อRUNNING=falseคงอยู่2sบนcalibrated landing. จอดระหว่างทางนับเป็นอีกsegment/tripตามนิยามนี้ ไม่เรียกเป็นการรับผู้โดยสาร. เก็บdefinitionVersionและraw-codejourneyแยกเมื่อลิฟต์ไม่สอบเทียบครบ
- **Runtime:** รวมช่วงRUNNING=trueที่มีknown coverage; สัญญาณไม่ทราบ/gap/commissioning workไม่เติมเป็นruntimeหรือidle
- **Idle time:** RUNNING=falseในช่วงที่ข้อมูลvalid; ไม่เท่ากับประตูเปิดหรือว่างไม่มีผู้โดยสาร
- **Floor visits:** confirmed stopตามนิยาม; ไม่ใช่ทุกcodeที่วิ่งผ่าน; W-05ระหว่างcodeNรายงานraw-code stopsแยกจากfloor visitsที่ทราบชื่อ
- **Data coverage:** known-valid monitored interval / scheduled monitoring interval; มีunknown timeแสดง. denominatorยึดmonitoring schedule/version ไม่ตัดช่วงofflineทิ้งแล้วรายงาน100%
- **Availability:** ระยะแรกเรียกtelemetry availability/coverageเท่านั้น; lift service availability/MTBF/MTTRต้องมีนิยามfault/downtime/ticketที่รับรองก่อนเปิดmetric
- **Hourly charts:** aggregationตามtimezoneAsia/BangkokแสดงกับUTC storage; gapเป็นnull/hatchedไม่ใช่0; backlogเติมประวัติได้พร้อมrecompute windowแต่ไม่ยิงlivealarmย้อนหลัง

กรณีcaptureจบก่อนtripจบ/ข้อมูลขาดระหว่างtripให้ `CENSORED/INCOMPLETE`, ไม่สรุปเวลา/ปลายทางเป็นจริง. unitfixtureต้องมีground truthอิสระและexpected counts ไม่deriveexpectedจากfunctionเดียวกับproduction

### D.5 Visual/performance acceptance

[Targets ที่เสนอ] 1920×1080เป็นbaselineตามต้นฉบับ; 3840×2160และ1366×768ต้องอ่านข้อมูลหลักได้ไม่มีตัวเลขทับกัน. ใช้reference screenshotตำแหน่งคงที่ในTEST, deterministic clock/random seedและข้อมูลไม่รวมtimestampsที่ทำให้visualdiffล้มทุกครั้ง

P95 Gateway-newline→UI-commit ≤2,000msในsteady LIVE/TEST; ส่งรายงานP50/P95/P99และmaxพร้อมsamplecount≥200. time-to-first-baseline/reconnect/backlog-drainวัดแยก ไม่เอาออกจากรายงานแล้วบอกว่าทุกกรณี≤2s

motionตั้งเป้า30–60fpsบนDellที่ใช้จริง; baseline testframe-time P95≤33.3msที่1080pพร้อม5ตู้/4กราฟและbrowserอื่นตามtestload. วัด4Kแยก หากไม่ผ่านให้ลดdecorativeeffectsก่อนลดความชัดของข้อมูล

soakขั้นต่ำ2hก่อนG-C, full24hในP6; ตรวจboundedarrays/chartpoints/listeners และmemory trendไม่มีการเติบโตต่อเนื่องที่อธิบายไม่ได้. ตัวเลขเป้าหมายนี้เป็นgateที่ทดสอบ ไม่ใช่คำรับประกัน hardwareที่ยังไม่ตรวจ

`requestAnimationFrame` callbackเป็นก่อนpaint [T6A]; ตั้งชื่อmetric `ui_commit`/`next_frame_callback`ตามสิ่งที่วัดได้ ไม่อ้างเวลาพิกเซลปรากฏจริง หากต้องcertify sensor→pixelต้องมีexternalmeasurement/fieldvideoพร้อมtimestampแยก

**G-U packet:** Operations/Presentation previews, frame reference comparison, live-capability matrix, W-04/W-05/UNKNOWN/STALE/DEMO screenshots และรายการจุดที่ต่างจากภาพ. PNGต้นฉบับใช้directionการออกแบบ ไม่ถือว่าownerรับมอบwebแล้ว

## 8. Deliverable E — Canary, Rollback และการขยายหน้างาน

### E.1 ก่อนขอ Gate G-C

ต้องผ่าน PRE-0/G-A, P0-SERVER, P1-OFFLINE, P2-TEST, HUD core/quality tests, minimum operational alarms, TLS/ACL/Auth, backup/restore baseline และ TEST fault matrixที่บังคับ. G-Uอย่างน้อยcore operationsต้องผ่านก่อนเรียกcanaryว่าdemo-ready; decorative world mapที่ยังไม่เสร็จต้องระบุว่าไม่ขวางdata proofแต่ยังไม่ถือvisualส่งมอบ

สร้าง `CANARY_PLAN_<liftCode>.md`, `CANARY_AUTHORIZATION.json`, `KNOWN_GOOD_CAPTURE_MANIFEST.json`, `RELEASE_COMPATIBILITY.json`, `ROLLBACK_RUNBOOK.md`. ระบุทุกaffected process/task/lift; hashrelease/runtime/config; sourcecontracttag; rollbackartifactที่ไม่importmoduleใหม่; currentSQLmigrationversion; maximum allowed capture gapที่เจ้าของยอมรับ

**ค่าเสนอ:** canary W-02 (เพราะเป็นtargetแรกในต้นฉบับ) แต่ต้องยืนยันว่าขณะดำเนินการยังเป็นตัวที่เหมาะและพร้อมที่สุด ห้ามเลือกแทนเจ้าของเพียงเพราะชื่ออยู่ในแผน; approvalต้องระบุลิฟต์และwindowจริง

Gate recordต้องมี `approvedBy, approvedAt, evidenceRef, targetMachine, liftIds, sourceRelease, targetRelease, contractHash, windowStart/windowEnd, expiresAt, allowedActions, rollbackAllowed, maxGapSeconds`. ทุกค่าที่ต้องownerยืนยันเริ่มnull; validationต้องfailถ้าrecordเก่า/หมดอายุ/scopeไม่ตรง

### E.2 การเปลี่ยนหนึ่งลิฟต์โดยไม่หยุดตัวอื่น

1. ยืนยันscopeกับผู้ดูแลก่อนเริ่มในwindow; บันทึกก่อนเปลี่ยน: sourcecounters/lastsamplesของทุกลิฟต์, taskstatus, disk/network, releasehash และtimezone ห้ามมีcountdownสั่งผู้ใช้ถอดสายเอง
2. ปิดเฉพาะสิทธิ์launcher/watchdogในการเริ่ม **ลิฟต์เป้าหมาย** ผ่านhandover ownership manifestที่ทดสอบแล้ว; taskของตัวอื่นทำงานต่อ ห้ามใช้global `STOP_CAPTURE` หรือ `Disable-ScheduledTask` ที่หยุดทุกลิฟต์ตามขั้นตอนเดิม
3. exporttask/launcherconfigก่อนเปลี่ยนและใช้immutable known-good copy; modeเปลี่ยนรายลิฟต์เป็น `HANDOVER_PENDING`, ไม่เปลี่ยนdefaultของfleet
4. หยุดloggerเป้าหมายด้วยวิธีที่PRE-0ยืนยันแล้ว. ถ้าไม่มีsingle-liftgracefulstopที่พิสูจน์ได้ ให้BLOCKEDcutover และทำdesign/authorizedtargetedstopเพิ่มก่อน ไม่เขียน `Stop-Process` สุ่มจากPIDอย่างเดียว. การterminateที่จำเป็นต้องได้รับอนุมัติและบันทึกpotentialgapอย่างตรงไปตรงมา
5. ตรวจprocessidentity/portclosed/leaseจริง ไม่ใช้การหายไปของpidfileเพียงอย่างเดียว; no dual-reader. preservecapturefiles; ทำprivateboundarymarkerในsidecarไม่rewritehistory
6. Agentacquireเฉพาะport/liftที่อนุมัติ; verify `LIFT=n` ปัจจุบันก่อนpublish. รอvalid STตามbaselinecadenceจริง; startupยังไม่freshให้UI `WAITING_SOURCE_BASELINE` ไม่เดาชั้น
7. ตรวจraw→decode→outbox→DB ACK→UI shaftกับลิฟต์จริงโดยผู้ดูแล ระบุการจอด/เดินทางที่ทำได้ตามการใช้งานปกติ ไม่แตะตู้/วงจรเอง; captureloggerตัวอื่นยังเดินและcounterไม่หยุด
8. ขั้นนี้ใช้publisher **MQTT end-to-end** ที่ผ่านP2แล้ว ไม่เพียงJSONLเหมือนB.3เดิม. localJSONLเป็นdiagnosticได้แต่ไม่ใช้แทนหลักฐานDatabase/Web
9. launcherรอบถัดไปต้องเห็นownershipเป้าหมายอยู่Agentและตัวอื่นอยู่loggerเดิม ไม่startแข่ง; ตรวจหนึ่งwatchdogcycleจริงพร้อมcontinuoushealth. writerhealthไม่ผูกกับจำนวนpublishถ้าbrokerขัดข้อง
10. [TARGET] สังเกตอย่างน้อย2ชั่วโมงและมี≥20confirmedtripsที่เกิดได้ตามสภาพจริง พร้อมchecksจำเป็น. ไม่เร่งคนใช้อาคารให้วิ่งtestครบ; ถ้าตัวอย่างไม่พอรายงานCANARY_OBSERVING/INSUFFICIENT_SAMPLE ไม่PASS
11. ส่งหลักฐานcanaryและผลrollbackdrillในsandbox/fieldที่อนุมัติ. หยุดรอG-Rก่อนขยาย

### E.3 เงื่อนไข rollback

rollbackทันทีภายในscopeที่ownerอนุมัติเมื่อเกิด identityผิดตัว, serialwriteattempt, rawcaptureไม่เดินทั้งที่ยืนยันinputกำลังมา, outputไม่ตรงmapping, recordสูญโดยอธิบายไม่ได้, readerอื่นหยุดจากcutover, หรือresourcepressureทำให้Captureเสี่ยง

กรณีBroker/Serverล่มแต่rawCapture+outboxยังเดินปกติ → `DELIVERY_DEGRADED`, ไม่รีบrollback/รีสตาร์ตreaderโดยไม่จำเป็น. หากsourceสงสัยเองให้labelquality ไม่ไปปรับmappingให้ผ่าน

ขั้นตอน: freezeการเปลี่ยนแปลง → blocktargetlauncher → stop/releaseAgentworkerเฉพาะเป้าหมายและverifyportrelease → start **known-good releaseในdirectory/runtimeของเดิม** ด้วยconfigเดิม → verifyrawcapture/baseline/identity → restoretargetownership → บันทึกgapและoutboxที่ยังไม่ACK. ห้ามลบSQLite/journalหรือคืนDatabaseเก่าเพียงเพื่อrollbackreader

หากsharedAgentworkerหยุดไม่ได้โดยไม่กระทบตัวอื่น ให้รายงานblast radiusและใช้approvalตามscopeใหม่ ไม่killAgentรวมโดยอัตโนมัติ. automaticfallbackต้องเป็นboundedstate-machine/lease-aware; ไม่มีวงจรAgentตาย→loggerเปิด→Agentฟื้น→แย่งCOM

[Targetเสนอ] **คืนknown-good rawcaptureภายใน120วินาทีหลังยืนยันportปล่อยแล้ว**; เวลาหยุดเพื่อhandoverและรอidentityวัดแยก. ค่าเดิม15นาทีถูกแทนด้วยเป้าหมายนี้เพื่อให้ตรวจว่าทำได้จริง ถ้าสภาพหน้างานทำไม่ได้ให้ขอownerยอมรับrecoverybudgetใหม่ก่อนG-C ห้ามรายงานว่าผ่าน120sโดยตัดช่วงที่มีปัญหาออก

### E.4 Rollout P3-FLEET

ลำดับเสนอ W-02 → W-01 → W-03 → W-05; G-Rต้องระบุลำดับ/ตัวที่อนุมัติจริง. ทำchangeทีละตัวและverifyaftereach; W-05ใช้profileเฉพาะ; W-04ยังไม่auto-enrollเพียงเพราะมีbeacon ห้ามใช้globalflagเปิดCaptureทั้งfleetโดยไม่มีscope

ช่วงhybridให้report `LOGGER_OWNED`, `AGENT_OWNED`, `HANDOVER_PENDING`, `NOT_COMMISSIONED` ต่างกันชัดเจน. monitoringdeploymentstatusไม่เปลี่ยนสถานะบริการลิฟต์โดยอัตโนมัติ

ระหว่างcutoverให้ `commissioningWindow` เพื่อตีความข้อมูลที่ถอด/ต่อสัญญาณอย่างถูกต้อง; บันทึกทุกอย่างตามจริง แต่ไม่ใช้ช่วงงานสายไปสร้างKPIการเสียของลิฟต์ หรือปิดcriticalalarmจริงของส่วนที่ยังmonitorอยู่ทั้งระบบ

## 9. Deliverable F — P3/P4/P5/P6 และการรับมอบ

### F.1 P3 — Fleet, History และ Analytics

หลังG-Rเพิ่มตัวที่อนุมัติ, EventExplorer/filter/cursor/export, deterministicaggregationตามD.4, coverage/gaps, mappingversionfilterและimportreconciliation. ต้องทดสอบreceivedlatehistory/updateaggregateโดยcurrentไม่ถอยและnotificationไม่ซ้ำ

trip/historyของW-05ที่ยังไม่สอบเทียบกลางต้องแสดงraw-codejourney; analyticsที่ต้องใช้physicalfloorlabelไม่รวมเป็นlabelที่เดา. retrospectivemappingcorrectionทำผ่านversionedreprocessjobแสดงว่าผลเก่า/ใหม่ต่างเพราะmappingไหน

### F.2 P4 — Alarm Center + Demo engine

แยก **condition** ACTIVE/CLEARED จากworkflowACK/CLOSEเพื่อไม่ทำให้ACKลบconditionที่ยังเกิดจริง; muteเป็นnotificationpolicyไม่ใช่ปิดmonitoring. minOpenSec2สำหรับSAFETY contactเป็นdiagnosticthresholdจากแผนเดิม ไม่เป็นการcertifyวงจรนิรภัย. ข้อมูลขาดขณะalarmactiveให้conditionUNKNOWN/last-known ไม่auto-clear

rulesdisabled FIRE/FIRE_RETURN/DOORสำหรับREALจนcommissioned; SIMเปิดเพื่อสาธิตได้แต่isolated. no-replay-notificationguardใช้ทั้งorigin/processingmode/currenteligibilityไม่เชื่อclientส่ง`source=live`อย่างเดียว

Demoengineมีscenario deterministic:ขึ้น/ลง/จอด/uncalibrated/gatewayoffline/alarm/ackdryrunในsessionเดียว. ใช้ชื่อThe Whizdomได้พร้อมbannerถาวร; stopdemoกลับLIVE snapshotไม่เอาตำแหน่งdemoมาปน. Testผู้ใช้หนึ่งคนดูDemoขณะที่อีกคนดูLiveและมีAlarmจริงในTESTenvironmentที่แยกdomain

### F.3 P5 — Presentation polish / DRY_RUN console

HUDvisualfidelity, mode/world-mapviewตามreference, reportlayoutและkeyboard/readability. CommandsเฉพาะDRY_RUNเพิ่มเมื่อไม่ขวางcoreHUD/fieldproof; approvalflowสองroleสาธิตได้แต่ต้องมี `notSentToHardware=true` และserverrefusesLIVEทุกกรณีของREAL

ไม่วางoutboxที่dispatchลิฟต์จริงเพื่อเตรียมไว้เผื่ออนาคตในPOCread-only; physicalcommandintegrationเป็นโครงการอนุมัติแยก

### F.4 P6 — Hardening และhandover

full24hsoak, boundedmemory/disk/queue, power/network/servicefaultdrillsที่อนุมัติ, backuprestoreพร้อมserverDataEpoch/reconcile, coldbootโดยไม่interactiveadminlogin, securityscan, dependency/licenseinventory, signing/hashmanifest, releasecompatibility, FAT/SAT/UAT และrunbooks

[G-H evidence] รวมรายงานที่ระบุเครื่อง/OS/browser/runtime/image digest/contracthash/liftprofileversions, latency distributions, samplesถูกต้อง, failurematrix, knownlimitations, gaps/RPO/RTOที่วัด และownerreviewของHUD. ปัญหาที่ownerยอมรับให้เป็นACCEPTED_RISKพร้อมscope/expiry ไม่เปลี่ยนเป็นPASSเงียบ ๆ

## 10. Test Strategy — ต้องสร้าง test ไม่ใช่เพียงเอกสาร checklist

รายการtest IDs/phase/expectedresultครบใน `TEST_MATRIX.md`. ชุดที่ต้องผ่านก่อนG-C คือทุกแถว `beforeCanary=true` ของ `execution-manifest.json` และG-A; field-onlytestsยังไม่ต้องPASSก่อนทดลองแต่ต้องมีrunbook/owneractionที่อนุมัติไว้

### 10.1 กลุ่มทดสอบที่ต้องมี

| กลุ่ม | สิ่งที่ต้องพิสูจน์ |
|---|---|
| Contract C-* | schema valid/invalid/composition/formats/int64/ACK/presence/ACL/compatibility; PythonกับNodeตรงกัน |
| Gateway G-* | parserbounds, no serialwrite, identity, perliftownership, timestamps, wrap/reboot, online debounce, journalrecover, resourcebounds |
| Delivery I-* | PUBACKไม่ล้างqueue, API-only/DB-only/Brokerfailure, crashก่อน/หลังcommit, ACKlost, duplicates/hashconflict, snapshot/backlogorder |
| Ordering O-* | durableSeqข้ามrestart, NTPclockback, epochre-enroll, copiedDB/dualwriter, WSbootstraprace/resnapshot |
| UI U-* | real-drivenmotion, nophantomfloors, W05rawtrack, W04correctservice, datagap, reducedmotion, realtimealarm, FPS/latency |
| Security S-* | realm/auth/ACL/ACKspoof/Origin/expiry, noprivatedata, neverREALcommand |
| Demo D-* | TESTtopicroutingครบ, per-sessionisolation, zeroREALcontamination, realmonitoringเดินต่อ |
| Ops P-* | scratchupgrade/restore/partitionboundary/queuepressure/coldboot/known-goodrollback/soak |
| Field F-* | consentedcanary, identity/floors, independentcapturecontinuity, rollback, sequentialrollout |

หากนำฟีเจอร์ที่เดิมอยู่ phase หลัง Canary มาเปิดใช้ก่อน เช่น Demo หรือ Analytics ต้องย้าย tests ของฟีเจอร์นั้นมาผ่านก่อนเปิดใช้ด้วย; `beforeCanary=false` ไม่ใช่สิทธิ์ให้ deploy ฟีเจอร์ที่เปิดแล้วแต่ไม่ทดสอบ. ฟีเจอร์ที่ยังไม่ผ่านต้องปิด routes/capabilities ไม่ตอบ success จำลอง

### 10.2 Failure-injection boundaries

ก่อนcanary faultinjectionทั้งหมดบนTESTและscratchvolumes ใช้COMfake/PTTY/recordedinput ไม่มีพอร์ตจริง. `LMS_AGENT_FORBID_SERIAL=1` ทำให้ทุกconstructorที่จะเปิดserialfailในCI. ตรวจno-writeด้วยAST/objectcapability/transitivemodulecheckและFakeSerial.writeที่raise; ห้ามgrepคำ`write(`แล้วล้มfile/dbwritesที่จำเป็นตามแผน

killprocess/dropACK/full-disk/clockjump/networkpartitionทำในcontrolledcontainers/VM/mocks. **ห้ามเปลี่ยนนาฬิกาWindowsของGatewayจริงเพื่อทดสอบNTPย้อน** ใช้clockinjection. databasecorruption/missingpartitiontestใช้testdatabaseที่confirmname/labelแล้วเท่านั้น

### 10.3 Evidence และpasscriteria

ทุกtestrunมี `runId, testIds, startedAt, finishedAt, duration, environment, sourceMode, commit, contractHash, result, assertions, artifacts`. artifactsrawprivateแยกredactedsummaryที่จะcommit. latencyrawsampleเก็บจำนวนdrop/excludedพร้อมเหตุผล ไม่คัดเฉพาะดี

P95sourceage/floorcorrectnessและalarmlatencyแยกmetric. DeadlinefieldNO_RXTXในฉบับนี้คือ **threshold90s → evaluator≤91s → UI≤93s** ภายใต้budget; ไม่เรียก≤90sจากสายขาดเหมือนDoDเดิมและซ่อนtickdelay. Gatewayheartbeatgap≤31sstate/≤33sUI. PhysicalLWTdelayตามMQTTkeepaliveไม่ถูกเอามารวมกับคำว่าafterreceipt≤3s

หากต้องการscreen≤90sจริง ให้ปรับthresholdลงพร้อมADR/acceptanceก่อน G-A ไม่เปลี่ยนthresholdในtestคนละค่ากับruntimeเพื่อผ่าน

## 11. Revised PHASES.md และลำดับทำงานที่อนุญาต

ใช้ `PHASES_REVISED.md` เป็นเนื้อหาต้นทางเพื่อmergeเข้า `docs/workflow/PHASES.md` ของทั้งสองrepo. เก็บชื่อP0–P6เดิมให้linkย้อนกลับได้ แต่แยกsubphaseและDoDใหม่; อย่าcopyold“livecutoverall”กลับมาจากREADME/CLAUDE.md

```text
PRE-0 (inventory/known-good/source diff)
  → A-DRAFT (Contracts + migration/schema tests) → STOP G-A
  → P0-SERVER (Dell TEST stack + security + backup baseline)
  → P1-OFFLINE / P1-SHADOW (parallelกับP0ได้หลังG-A; noCapturechange)
  → P2-TEST + HUD-CORE (end-to-end TEST + failureproof) → G-U core review
  → G-C เฉพาะหนึ่งลิฟต์ → P2-CANARY → STOP G-R
  → P3-FLEET / HISTORY / ANALYTICS ทีละตัว
  → P4-ALARMS/DEMO → P5-PRESENTATION/DRY_RUN
  → P6-HARDENING → G-H
```

**Minimumoperationalalarms/security/backupของP0/P2มาก่อนcanaryอยู่แล้ว** ไม่รอP4/P6. FullAlarmCenter/notificationdesignเพิ่มทีหลัง ไม่ย้ายbasicfaultvisibilityกลับไปท้ายphase

### 11.1 Dependencyของเอกสารและworkflowtooling

หลังreviseแต่ก่อนrunphaseให้sync `CLAUDE.md`, BackendPlanreference, UXUIreference, `docs/workflow/PHASES.md`, `.claude/commands/phase.md`, deploy/testscriptsและrunbooksที่พบจริง เพิ่มsupersedednoteและlinkแผนนี้ ไม่rewriteบันทึกหน้างานเก่า

workflowplugin/hookใช้เมื่อมีจริงในenvironment ตรวจCLIจริงก่อนเรียกชื่อcommandsจากข้อความเก่า ถ้าpluginไม่ติดตั้งให้ใช้test runnerโดยตรงพร้อมreport ไม่ตั้ง`plugin validation`เป็นหลักฐานว่าระบบลิฟต์ผ่านและไม่installplugin/อัปเกรดCLIบนGatewayเองเพื่อให้phaseจบ

สคริปต์run/deployออกแบบ `-PlanOnly`เป็นdefault พร้อมexplicit `-Execute`/machine-role/gate-file. การใช้ชื่อphaseเดียวต้องไม่ทั้งbuildทั้งstopserviceจริงโดยไม่มีstepแยก

### 11.2 Release compatibility

`RELEASE_COMPATIBILITY.json` map `edgeRelease, platformRelease, contractVersion/hash, schemaMigrationRange, producerEpochs, signalConfigVersions, floorProfileVersions, testedMatrix, knownGoodRollbackRelease`. deployPlatformไม่แฟลชfirmwareหรือrestartreaderเอง

contractupgradeรับincomingversionที่ผ่านmatrixก่อน, upgradeGatewayทีละตัว, deprecateเก่าภายหลัง. มีtagและhashซ้ำไม่ได้; SDKgeneratedcodeไม่แก้ด้วยมือ หากสัญญาเปลี่ยนหลังG-Aต้องออกcandidateใหม่และกลับไปgateนั้นเฉพาะscope ไม่pretendownerอนุมัติทุกfutureversion

## 12. Open Items / กฎเมื่อมีสิ่งที่ยังไม่ทราบ

| Item | ตั้งต้น | สิ่งที่ทำต่อได้ | สิ่งที่ต้องรอ |
|---|---|---|---|
| วันที่สาธิต | ไม่ทราบ | พัฒนา/ทดสอบตามgates | ไม่ตั้งdeadline/ตัดDoDเอง |
| Dellจริง/OS/license/runtime | ต้องตรวจ | contracts/unit/simulator source | DB/stack/boot/graphicsfieldproof |
| `lms-ng` remote/access | ต้องตรวจ | localbranch/docs | push/visibilityเปลี่ยนเองไม่ได้ |
| Lift4พร้อมใช้งาน | รายงานoutofservice | config/UNKNOWN/NOTCOMMISSIONED UI | bindเพิ่มmonitoringต้องownerอนุมัติ |
| FIRE/FIRE RETURN | ยังไม่activated | SIMtestsและdisabledcapability | REALmode/Alarmจากสัญญาณนี้ |
| W05middlefloors | code3..46unknown | rawcodemotion/historyตามD | physicalfloorlabel/visitsที่อิงanchorไม่ทราบ |
| Known-goodrelease/stopone-liftmethod | ต้องพิสูจน์ | offlineimplementation | canaryblockedจนrollbackพร้อม |
| Rawdataที่จะpublicได้ | ยังไม่ยืนยันรายไฟล์ | synthetic/redactedfixtures | publishrawlog/credentials/privateconfig |
| Supportversionsของdependencies | targetจากS1 | compatibilityresearch/lockdraft | installonproductionโดยพลการ |

BLOCKEDเฉพาะงานที่ขึ้นกับข้อมูลนั้น; ทำงานofflineที่ปลอดภัยต่อได้ และส่งรายการที่ต้องowner/fieldoperatorทำอย่างเจาะจง ห้ามใช้ความไม่พร้อมหนึ่งเครื่องเป็นเหตุลดtestหรือทำทุกอย่างบนGatewayแทน

## 13. รายการส่งมอบสุดท้าย

1. **Contractsจริงที่ผ่านG-A** พร้อมbaseline diff, releasehash, examples, schema validators และvendorpin ทั้งสองภาษา.
2. **Edgeagent** replay/shadow/liveแยก, read-only, durableoutbox+DB ACK, identity/ownership, diagnostics และknown-goodrollback.
3. **Platformmonorepo** API/ingestion/current/history/SQLmigration/auth/WS/infra/backup/runbooks ที่ติดตั้งได้บนเครื่องเป้าหมาย.
4. **HUDตามreference** Operations+Presentation, shaftmotion,เลขชั้น/quality/health/events, sessionDemo และAnalyticsตามนิยามที่รับรอง.
5. **Evidencepack** testmatrix, contracthash/commits, latency/FPS/soak, failure/restore/canary/rolloutrecords, acceptedrisks และรายการNOT_RUN/BLOCKEDที่ยังเหลือ.

**Definition of Complete:** ไม่ใช่เพียงcodeถูกpush แต่เจ้าของเห็นข้อมูลลิฟต์จริงที่ตรวจสอบที่มาได้บนHUDที่รับรอง ระบบเก็บข้อมูลเดิมมีทางคืนที่ทดสอบแล้ว และทุกclaimเรื่องrealtime/durability/qualityมีevidenceตรงกับscopeที่รับมอบ

## 14. สิ่งที่ Claude ต้องทำเมื่อได้รับไฟล์นี้ครั้งแรก

อ่าน `CLAUDE_CODE_START_PROMPT_TH.txt` และ `PHASES_REVISED.md`; เริ่มPRE-0แบบไม่เปิดport/ไม่หยุดservice จากนั้นสร้างDeliverableAเป็นDRAFTและvalidationบนเครื่องที่อนุญาต ส่งdiff/decisionpacket/hash/tests แล้ว **หยุดที่G-A**. ห้ามไปP1-LIVE/cutoverเพราะข้อความในแผนเก่าบอกให้ทำต่ออัตโนมัติ

หากเพียงเริ่มsessionใหม่ของงานที่เดินอยู่ ให้ตรวจWORKFLOW_STATE/gateevidenceแล้วresumeจากnextAllowedAction ไม่เริ่มrepoใหม่ทับของเดิมและไม่ข้ามgateที่ยังpending
