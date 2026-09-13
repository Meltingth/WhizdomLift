# LMS-NG Backend Implementation Plan — Whizdom The Forestias POC v1.3

**Scope:** Backend API + Database + Realtime + gateway integration driving the designed UI (frames 02/02b/02c/02L → 03–09).
**Inputs:** TDS v1.0, OpenAPI v1, MQTT Topic Spec v1, PostgreSQL Schema v1, UX/UI Design Spec v1.0 (+refinements), **`Meltingth/WhizdomLift` repo — fully reviewed 2026-09-01**.
**Date:** 2026-09-01 · **Status:** v1.3 = v1.2 + the owner's scoping answers (2026-09-01): customer demo shows **The Whizdom only** (real 5 lifts), FIRE deferred until the activation test, an in-app **Demo Mode** replaces the simulated-tower story, and the on-site deployment is fixed to the two existing PCs. Marks: ⟲ v1.1 · ⟲⟲ v1.2 · ⟲⟲⟲ v1.3.

---

## 0. Executive summary / สรุปสำหรับผู้บริหาร

**TH —** อ่าน repo ครบแล้ว ระบบจริงคือการอ่าน**หน้าสัมผัสรีเลย์**จากตู้ควบคุมลิฟต์ด้วย Arduino Mega ต่อลิฟต์หนึ่งตัว (รหัสตำแหน่ง 6 บิต + RUNNING/SAFETY/UP/DN และ FIRE ที่ยังไม่เคยถูกกระตุ้น) ส่งบรรทัดข้อความ `ST` ทาง **RS485 ขาเดียว-ส่งออกอย่างเดียว** คนละคู่สายเข้าเครื่อง **Gateway PC (Windows)** — ดังนั้น "LMS gateway agent" คือซอฟต์แวร์บนเครื่องนั้น ไม่ใช่ firmware ใหม่ **ไม่ต้องแก้ firmware แม้แต่บรรทัดเดียว** (ออกแบบมาดี: ส่ง mask ทั้งพอร์ต ให้ฝั่ง PC ตีความใหม่ได้โดยไม่ต้องแฟลช) จุดที่กระทบแผนแรงที่สุด: **ช่องทางนี้สั่งงานกลับไม่ได้ทางกายภาพ** → โหมดคำสั่งบนลิฟต์จริงเป็น DRY_RUN ถาวรใน POC และ **ลิฟต์ 2 พร้อมใช้แล้ววันนี้** (HEALTHY ผ่าน RS485 บนเครื่อง Gateway, blind test ระบบถอดรหัส 14/14) จึงเป็นเป้าของ vertical slice แรก

**EN —** The repo resolves every §4 unknown. Real chain: lift controller relay contacts → per-lift Arduino Mega (read-only by hard rule) → one-way RS485 text stream `ST <ms> <52-bit mask>` @115200, one twisted pair per lift → per-lift USB dongle → a Windows Gateway PC. The LMS gateway agent is a Python service on that PC absorbing the proven `log_lift.py` duties and publishing MQTT per Topic Spec v1. No firmware changes needed (v1.2.2 already self-arms, heartbeats every 60 s, announces `LIFT=<n>` every 30 s). Commands are physically impossible on this channel; the write path is out of POC scope by hardware design, not policy. Lift 2 is verified healthy end-to-end today and is the B1 target.

### 0.1 Decided and unchanged (from v1.0)
Topic root/envelope/dedupe per MQTT Spec v1 · PostgreSQL Schema v1 as-is · OpenAPI v1 + WS channels per TDS §9 · painted enums are contractual · P95 telemetry→screen ≤ 2 s · supervisory-only stance.

### 0.2 ⟲ What the repo review changed (v1.0 → v1.1)
| # | v1.0 assumed | Reality (repo) | Plan impact |
|---|---|---|---|
| 1 | RS485 protocol from lift controller to decode | Relay dry contacts → Arduino per lift; "protocol" is the sketch's own `ST` text line | §4 rewritten as a concrete signal map; no vendor protocol work at all |
| 2 | Gateway = device speaking MQTT (Pattern A/B/C) | Gateway = **Windows PC** receiving 5 independent one-way serial streams | Agent = Python service on that PC (Pattern C-prime, §2) |
| 3 | Possible write path for commands | **TX-only MAX485 (DE/RE tied high, RO disconnected)** + never-OUTPUT rule | Commands DRY_RUN permanently on real lifts (§5.4) |
| 4 | Door state, operating modes available | Only floor code, RUNNING, SAFETY, UP, DN (+FIRE/FIRE-RETURN pins not yet identified) | statusPoints trimmed; UI door field absent for real lifts (design refinement #7) |
| 5 | State refresh every ≤5 s | ST on change + heartbeat re-emit every **60 s** idle; identity every 30 s | Freshness thresholds per gateway type: real `staleAfterSec=90`, sim 30 (§5.2; design refinement #6) |
| 6 | Firmware needs NTP/eventTime | Board has only `millis()`; resets per boot | `eventTime` = Gateway-PC wall clock (NTP) at line receipt (§2.2) |
| 7 | 3 towers / 16 lifts as primary fixture | **One building: labels B1,1…44, skipping 7 & 19; 5 lifts; codes 1–46** | Seeds re-cut (§6.2); demo = this real tower first; other towers simulated only if kept (refinement #7) |
| 8 | 5 real lifts ready | Lift 2 ✅ (on Gateway, COM20) · Lift 3 ✅ ref (old FW, no LIFT id) · Lift 1 🔴 VS2 dead + no power · Lift 4/5 ⏳ | B1 targets Lift 2; commissioning checklist per lift (§8 B0-R) |
| 9 | B0 = protocol discovery ahead | **B0 essentially done**: decode proven, blind test 14/14, health tooling mature | B0 shrinks to residuals; timeline moves left (§8) |

**⟲⟲⟲ v1.3 additions:** #10 Demo Mode (source switch, DEMO banner, zero persistence); #11 single-building UI (no selector) + `รอติดตั้ง` commissioning state excluded from KPI denominator; #12 demo scenario v2 on W codes (fire recall 34→1, ground label "1").

**⟲⟲ v1.2 alignment additions:** #8 Alarm Center naming = "ศูนย์สัญญาณเตือน" (toast subline still says "หน้ารายการสัญญาณเตือน"); #9 default view = The Whizdom, on-duty user Joy / ACK actor Nok; W cards currently print "NORMAL · door CLOSED" — the build must omit the door line for real lifts (no signal exists).

**Design-impact ledger (carry to the Claude Design project as refinements):** **#6** freshness bands/staleAfterSec are per-asset config (a healthy idle real lift legitimately shows `↻ 58s`); **#7** the real tower's shaft uses floor list `B1, 1–6, 8–18, 20–44` (labels 7/19 skipped; ground = "1", not "G") and its ElevatorCards show no door line; RUNNING can surface as a status point.

---

## 1. POC architecture & on-site deployment (⟲⟲⟲ resolved to the two existing machines)

```
[ตู้ลิฟต์ 5 ตู้: Arduino Mega + MAX485 TX-only]
        │ RS485 one-way, one pair per lift (×5 dongles on USB hub)
        ▼
┌─ PC #1 — Industrial PC · "GW-WHZ-01" (Windows) ──────────────────────────────┐
│ lms_gateway_agent (Python, NSSM service, account `lmsagent`)                 │
│ · port→lift binding by FW banner (LIFT=1/2…; LIFT=0 & unknown ⇒ refuse+flag) │
│ · decode/debounce · capture_lift_N.log dual-write · sqlite outbound buffer   │
│ · publishes MQTT/TLS →                                                        │
└───────────────┬──────────────────────────────────────────────────────────────┘
                │ LAN (static IPs, e.g. GW .11 → SRV .10 : 8883 only)
                ▼
┌─ PC #2 — Dell · "LMS-SRV" (Windows + Docker Desktop/WSL2) ───────────────────┐
│ docker compose: EMQX · PostgreSQL 16 · Redis 7 · apps/api (NestJS)           │
│ · apps/web · demo-engine (tools/simulator repurposed, §5.5)                  │
│ · Chrome kiosk → จอ NOC (the same machine drives the wall monitor)            │
│ · NTP server for the LAN (syncs internet when available; GW syncs to SRV)    │
│ · nightly pg_dump → local disk + copy to PC #1 (cross-machine backup)        │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Role rule:** PC #1 does nothing but capture + publish (its job is to never die); everything stateful lives on PC #2. If PC #2 is down, the agent buffers to sqlite and replays with original `eventTime` on recovery — no data loss, and the drill is part of B-week testing.
**PC #2 requirement:** ≥ 16 GB RAM, SSD ≥ 100 GB free, virtualization enabled (WSL2). Verify with `systeminfo | findstr /i "memory"` before W1; if the Dell is below spec, swap roles is NOT the fallback (capture isolation wins) — a mini-PC or enabling the stack on a site server is.
**Network hardening (B5):** Windows Firewall — SRV allows 8883 inbound from GW's IP only, 80/443 for LAN browsers; EMQX per-client credentials + ACL; TLS with a site CA (scripts in `infra/`); both PCs on UPS.

## 2. ⟲ Gateway integration — RESOLVED

**Division of roles is already agreed in the repo (CLAUDE.md §9.5):** the front-of-cabinet machine plans/debugs/flashes over USB; the Gateway PC receives all five lifts continuously. The LMS agent lives on the Gateway PC.

### 2.1 Wire contract (frozen — implemented by firmware 1.2.2, do not change)
| Line | Cadence | Meaning |
|---|---|---|
| `FW IODebug <ver> <date> LIFT=<n>` | boot + every 30 s | Build + lift identity. `LIFT=0` = build forgot the flag (self-reporting). Lift 3 still runs 1.0.x → emits **no** FW line (see 2.2 identification fallback) |
| `ST <board_ms> <13-hex>` | on any pin change + re-emit after 60 s idle + baseline at boot | 52-bit mask, bit i = pin D(2+i), **1 = HIGH**; contacts are INPUT_PULLUP so **active = 0** (decoder inverts). Whole-port mask ⇒ signal remap is PC-side config, never a reflash |
| human-readable banner/help lines | boot / USB commands only | Ignored by parsers (`rejected` counter guards format drift) |

115200 baud, one-way. Anything the backend needs beyond this (timestamps, identities, health) is the **agent's** job.

### 2.2 `lms_gateway_agent` (Python, on the Gateway PC — extends, then replaces, `log_lift.py`)
Windows opens COM ports exclusively, so the agent **absorbs** the capture duties rather than running beside them, preserving every hard-won behavior in the repo's CLAUDE.md §6:

1. **Port→lift identification:** enumerate ports (Status OK only), open with `dtr=False, rts=False`, wait for `FW … LIFT=n` (≤35 s). Boards without an FW line (Lift 3) fall back to an explicit `--map COM<x>=3` config **with the same refuse-to-mislabel guard** as log_lift.py; a mid-capture identity change (dongle swap) severs and re-binds, never silently relabels.
2. **Per-line processing:** parse `ST` (regex + **length check** — a 12-nibble mask parses but shifts every bit); reject counter per lift exported as `data_quality.rejectedLines` (must stay 0; >0 ⇒ DATA_QUALITY alarm §5.3). `eventTime` = PC wall clock at receipt (PC syncs NTP; board_ms kept for segmentation only — split on regression = board reboot ⇒ emit `BOARD_RESTART` event).
3. **Debounce/decode:** the repo's proven two-layer per-pin algorithm (`debounce_pins`: hold 60 ms per pin, settle 150 ms per composite state) ⟲ supersedes the generic 250 ms whole-state default for these inputs; then position formula `code = Σ 2^i·VSi` and `CODE_TO_LABEL` (§4.2).
4. **Publish (Topic Spec v1, unchanged envelope):** retained `telemetry/elevators/{elevatorId}/state` on every accepted change **and** on the 60 s board re-emit; `events/elevators/{elevatorId}` per debounced signal change; agent `status/birth|heartbeat(10 s)|will` with per-lift `lifts[id].rxtx` (OK if any line ≤75 s, NO_RXTX past 90 s — thresholds from the repo's own 75 s listen check); `diagnostics/network` with per-lift rejected/reconnect counters.
5. **Buffering & lifecycle:** sqlite outbound queue (broker down ⇒ queue, replay oldest-first with original eventTime); `bootId` per agent process, `sequence` monotonic; run as a Windows service (NSSM/Task Scheduler), fail-fast on a wrong port before first data (3 tries) then reconnect forever after — exactly log_lift.py's rule; `STOP_CAPTURE` respected; keep appending `capture_lift_N.log` in the existing format so the analysis toolchain and the repo's commit-everything workflow stay intact.
6. **No writes to the serial port, ever** (`rs485_check.py` discipline): the link is one-way; the agent never transmits.

**Why Python, not the TDS Go agent (POC decision):** the decode/debounce/identification logic already exists and is field-proven in Python on this exact machine (pyserial installed, lessons encoded); porting to Go now adds risk with zero demo value. The MQTT contract is language-neutral, so a Go port remains a clean production option (ADR to record).

---

## 3. UI → contract traceability (v1.0 table stands; ⟲ three rows change)

The full mapping table in v1.0 §3 remains valid. Deltas:

| UI element | ⟲ Change |
|---|---|
| door OPEN/CLOSED | Real lifts publish **no** `DOOR_OPEN` key → the card/detail row is absent (UI renders only present keys). Simulated lifts keep it. |
| Freshness `↻` / stale | `staleAfterSec` resolved per elevator from its gateway type: **real = 90 s, simulated = 30 s**, carried in the status payload so the client needs no lookup. An idle real lift at `↻ 58s` is healthy. |
| StatusPoints matrix (03) | Real lifts: `RUNNING`, `SAFETY_DEVICE` (true = closed = normal), later `FIRE_OPERATION` / `FIRE_RETURN` once pins are identified. `RUNNING` also drives a subtle "กำลังวิ่ง" affordance the shaft already implies. |

Also new: `dataQuality` may carry `positionResolution: 2` (Lift 1 until VS2 is repaired) and `rejectedLines`.

## 4. ⟲ Signal map & decode specification (concrete — from the repo, verified)

### 4.1 Per-lift signals (reference wiring = Lift 3; Lift 2 identical; 10 lines total)
| Pin | Signal | Semantics (measured) | Normalized to |
|---|---|---|---|
| D24–D29 | VS2–VS7 | 6-bit **plain binary** position code, LSB = VS2; codes 1–46; single-step verified 100 % | `floorRaw` = code (string), `floorDisplay` via §4.2 |
| D16 | RUNNING 运行 | closed while moving (up **and** down 100 %), open at rest (12 % closed while stopped = leveling) | `statusPoints.RUNNING`; feeds trip analytics later |
| D17 | SAFETY 安全 | normally-closed; opens on fault. ⚠ 8 brief opens observed with unknown meaning (repo task 6) | `statusPoints.SAFETY_DEVICE` (true = closed). Alarm only when open **> 2 s** until semantics are confirmed |
| D19 / D20 | UP 上行 / DN 下行 | perfectly exclusive while travelling (100 %/0 %) | `direction`: UP / DOWN; neither + not RUNNING ⇒ IDLE; both closed ⇒ `UNKNOWN` + dataQuality flag |
| (pending) | FIRE 火灾 · FIRE RETURN | contacts exist on terminals 16/20; **pins unidentifiable until physically triggered** (open contact ≡ unconnected) | `statusPoints.FIRE_OPERATION` / `FIRE_RETURN` + `operatingMode=FIRE` — enabled only after the activation test (§8 B0-R) |

Active-low inversion (`ACTIVE_LOW=True`) happens once, in the agent. `operatingMode` = `NORMAL` unless FIRE (no maintenance/inspection contact exists on this wiring).

### 4.2 Floor mapping (single real tower — identity to confirm, §12-R1)
Building labels **B1, 1–6, 8–18, 20–44** (7 and 19 skipped, per operator + offset evidence). Calibrated anchors: `1→B1, 2→1, 12→9, 22→20, 28→26, 34→32, 35→33, 38→36, 39→37, 46→44`; offset is a constant **+2 from label 20 to 44** (interpolate all of 22–46 accordingly); the 1–9 ladder has **two unresolved hidden landings** — until repo task 4/5 closes it, unresolved codes render as `code N` with `dataQuality.floorUncalibrated=true` (UI shows the mono code, never a guessed label). `core.floor_mapping` seeds exactly this table; **`floorRaw` stays the opaque code string**.

### 4.3 Per-lift deviations (agent config, mirrors LIFT_STATUS.md)
| Lift | Condition | Agent behavior |
|---|---|---|
| 1 (B) | VS2 line dead (bit 0 never toggles; top code 23) + board currently unpowered | Use reference map; detect the fault live (bit 0 silent across ≥8 floor changes) ⇒ `dataQuality.positionResolution=2` + `SENSOR_VS2_FAULT` alarm; clears itself after repair |
| 2 (C) | ✅ healthy on Gateway COM20, FW 1.2.2 LIFT=2 | **B1 vertical-slice target** |
| 3 (A) | ✅ healthy reference; FW 1.0.x → no identity line | `--map` fallback until reflash at front-of-cabinet machine |
| 4 (D) / 5 (E) | untested / number inferred | Commission per repo checklist before tagging `REAL`; Lift 5 numbering must be confirmed |

## 5. Backend processing logic (v1.0 stands; ⟲ deltas)
- **5.2 Liveness:** thresholds split by gateway type — real lifts: `INTERFACE_NO_RXTX` when no line for 90 s (agent flags at 75 s), `STALE` when `now−eventTime > 90 s` with link up (rare: means lines flow but decode stalls); simulated: 30 s as designed. `GATEWAY_OFFLINE` = agent LWT / 3×10 s heartbeats missed. Unchanged otherwise.
- **5.3 Alarm seed changes:** `FIRE_OPERATION`/`FIRE_RETURN` seeded **disabled** until the activation test maps the pins; `SAFETY_DEVICE_TRIP` requires open > 2 s (task-6 unknown brief opens must not page anyone); `DOOR_OBSTRUCTION` scoped to simulated lifts only; **add** `SENSOR_VS2_FAULT` (MAJOR, rule §4.3) and `DATA_QUALITY` (WARNING, `rejectedLines > 0`). Others unchanged.
- **5.4 Commands:** the real channel is **transmit-only by hardware** (MAX485 DE/RE strapped high, RO disconnected; never-OUTPUT rule protects the ports). Therefore: real lifts = `commandMode: DRY_RUN` **permanently in this POC** — interlocks evaluate on real data, the gateway result is simulated, stepper shows the DRY RUN chip; the full ACCEPTED→EXECUTED demo runs on simulated lifts; any future LIVE path is new certified hardware + lift-engineering sign-off, tracked outside POC scope. State machine, outbox, idempotency, approval flow: unchanged.

### 5.5 ⟲⟲⟲ Demo Mode — "ปุ่ม Demo" ที่ซื่อสัตย์ (owner answer #5)
The customer demo must show the complete future system (fire recall, door events, command execution) without faking data on the live record. Design:
- **A source switch, not injected data.** `POST /api/v1/demo/start` (admin/supervisor only) flips the realtime hub's source from `live` to the **demo engine** (the repurposed simulator), seeded from the latest real snapshot of the 5 W lifts so the transition is seamless; `POST /demo/stop` (or the demo script ending) snaps back to live instantly.
- **Nothing persists.** Demo telemetry/alarms/commands flow only through the hub and a `demo:*` Redis stream — never into `telemetry.*`, `alarm.*`, `command.*`, analytics, or audit (except one audit row: demo started/stopped, by whom).
- **Visibly labeled.** While active: persistent top banner `โหมดสาธิต — ข้อมูลจำลองเพื่อการนำเสนอ` + `DEMO` chip on every alarm row, toast, and command stepper (the 02L frame's "DEMO LOOP" chip generalized). Exiting restores the live view in ≤ 1 s.
- **Scenario v2 (W-coded, full-capability):** W-02 CRITICAL `FIRE OPERATION` — recall 34 → 1 (ground = "1" in this tower) with door-open on arrival; W-05 (Lift Service) MAJOR `DOOR OBSTRUCTION` during loading, ACK by Joy; command `PARKING` on W-02 with dual approval (Krit) ending `EXECUTED (DEMO)`. Door state and FIRE appear **only** in Demo Mode until the real FIRE pins are identified; the live view renders only signals that exist.
- Trigger UX: a discreet `สาธิต` button in the admin/user menu (not on the operator's main chrome) plus `Ctrl+Shift+D`.

## 6. Database plan (⟲⟲⟲ seeds re-cut: The Whizdom only; simulated towers removed from the customer system)
- **Site:** `Whizdom The Forestias` → one building **`WHZ` The Whizdom** (customer's real name for the tower). The Destinia/Mytopia/Petopia fixtures move to `packages/test-fixtures` for development and the demo engine — they are **not seeded** into the customer database and the building selector disappears from the UI (single-building product view).
- **Elevators (5):** `W-01…W-04` โดยสาร 01–04, `W-05` "Lift Service" — `LIFT_ID 1…5` per the owner's table (real building numbers; test labels A–E are wiring accidents and appear nowhere). All `tags=['REAL']`.
- **Commissioning semantics (new):** `elevator.enabled=true` only when its board is flashed with the correct `LIFT=` and linked at the gateway. Today: **W-01 ✅, W-02 ✅** · W-03 board on old 1.0.x (bind via agent `--map COM<x>=3` until reflashed) · W-04/W-05 not yet connected. Un-commissioned lifts render as neutral `รอติดตั้ง` (pending install) — never as faults — and are **excluded from the KPI denominator** (`ออนไลน์ 2/2` today, growing to `5/5`). The agent refuses to bind any port announcing `LIFT=0` or an unknown id and raises a commissioning flag (owner's "ผิดแบบเห็นได้" principle).
- **floor_mapping (WHZ):** §4.2 table verbatim — landings `B1, 1–6, 8–18, 20–44`; ground label is **"1"**; uncalibrated codes flagged.
- **signal_point / gateway / binding:** unchanged from v1.2 (`GW-WHZ-01`, `iodebug-st` 1.2.2, `device_address = LIFT_ID`), FIRE/FIRE_RETURN rows `enabled=false` until the activation test (owner answer #5 — deferred).
- **Users:** Joy (operator, on duty), Krit (supervisor), Beam (technician), Oat (admin). (Nok retired from the fixture — single-operator story now.)
- Everything else in v1.0 §6 (migrations, partitions, auth, interlock config, read models) unchanged.

## 7. API & realtime (v1.0 stands; ⟲⟲ two alignments)
- Status payloads carry `staleAfterSec` and `dataQuality` through to the client (already in `ElevatorStatus.dataQuality`).
- **Building scope (⟲⟲⟲):** single building — no selector; `GET /elevators?siteId` returns the 5 W lifts; KPI denominator = commissioned lifts only.
- **Demo Mode endpoints (⟲⟲⟲):** `POST /demo/start`, `POST /demo/stop` (role-gated), WS envelope gains `source: "live"|"demo"`; clients render the DEMO banner from that flag alone.
- **Simulator (`tools/simulator`) takes its constants from the frame, verbatim:** `design_extract/02L_design_extract.json` — `FLOOR_SEC 3`, dwell 4–8 s, tick 100 ms, per-lift patrol `routes` (`home/partial/legs/doors`), story clock (T0 12:29:41; MAJ_OPEN 12:30:12, MAJ_ACK 12:31:00, CRIT_OPEN 12:31:24; D-02 fire glide 10 s), freshness model for simulated lifts. The simulator runs in real time (no 52 s loop); story steps are triggered by `POST /dev/scenario/{step}`.

## 8. ⟲⟲⟲ Build plan — relative weeks (demo date TBD; gate list at the end)
| Week | Scope | Exit checkpoint |
|---|---|---|
| **W1 — First light** | PC #2: Docker stack, migrations, W-only seeds; agent built on PC #1 (proven first against `capture_lift_2.log` replay, then live); Lift 1+2 publishing; dashboard wired REST+WS; kiosk mode | **W-01 & W-02 live on the wall** ≤ 2 s P95; pull a dongle ⇒ `INTERFACE_NO_RXTX` ≤ 90 s; stop the stack 5 min ⇒ agent replays backlog cleanly |
| **W2 — Fleet & states** | Lift 3 via `--map` (reflash opportunistically); commissioning flow for 4/5 when boards land; `รอติดตั้ง` state; events/history + Event Explorer; freshness thresholds (real 90 s) | 3 lifts live; un-commissioned lifts look intentional, not broken; a healthy idle lift never flags STALE |
| **W3 — Alarms & Demo Mode** | Alarm engine with the signals that exist (SAFETY_TRIP > 2 s, INTERFACE_NO_RXTX, GATEWAY_OFFLINE, STALE_DATA, SENSOR_VS2, DATA_QUALITY); Alarm Center + ACK + audit; **Demo Mode engine + banner + scenario v2** | Real alarm pipeline ≤ 3 s (drill: unplug dongle → ACK it); demo button plays the full W-02 fire story and exits to live ≤ 1 s with zero rows persisted |
| **W4 — Commands & polish** | Command console `DRY_RUN` on live (hardware-honest interlock text), `EXECUTED (DEMO)` path in demo; visual polish against the design frames; §15 acceptance sweep | Operator→supervisor approval flow demoable both modes; grayscale/§9 audit passes |
| **W5 — Hardening & rehearsal** | TLS/firewall/UPS checks, NTP chain, backups + restore test, runbook (start/stop/failure drills), full 10-min rehearsal with the building-management script | `docker compose up` + NSSM service from cold boot to working wall in < 10 min; rehearsal signed off |

**Demo-readiness gate (must all be green before the date is set):** ≥ 2 real lifts live · demo button rehearsed · resilience drill (dongle pull + stack restart) clean · runbook printed for the NOC.
**10-minute demo flow v2:** Act 1 live — จริง สด (point at a moving W lift, pull one dongle live to show honest failure states) → Act 2 press `สาธิต` — the complete-system story (fire, doors, command) under the DEMO banner → Act 3 back to live in one second + availability/analytics talk track.

## 9. Technology decisions — one row changes
Edge: ⟲ **Python 3.12 agent on the Gateway PC** (pyserial, paho-mqtt, sqlite3; packaged as a Windows service via NSSM). Go `apps/gateway-agent` deferred to production (ADR-001). All other rows from v1.0 stand.

## 10–11. Security & repo layout (v1.0 stands; two notes)
The agent's MQTT credentials live in the PC's credential store, not the repo; `lms_gateway_agent.py` should live **in the WhizdomLift repo** beside the lessons that shaped it (respecting its commit-and-push-always rule), with `lms-ng` consuming it as a submodule at `firmware/rs485-gateway`.

## 12. ⟲⟲⟲ Decision log (owner answers 2026-09-01) & what's still open
| # | Decision |
|---|---|
| 1 | Audience = **ทีมบริหารอาคาร**; demo **on-site** against the real Gateway PC |
| 2 | Deployment = the two existing PCs per §1 (Industrial = gateway agent · Dell = stack + kiosk) |
| 3 | Customer view = **The Whizdom only** (option ก); simulated towers demoted to dev fixtures |
| 4 | "The Whizdom" is the customer's real name for the tower |
| 5 | FIRE deferred — live view shows only real signals; the **Demo Mode button** (§5.5) carries the complete-system story |
| 6 | W-05 real name = **Lift Service** |
| 7 | LIFT_ID = real building numbers 1–5 (labels A–E are wiring order only); W-01 & W-02 flashed ✅; W-03 old FW (map fallback); W-04/W-05 not yet connected; `LIFT=0` = visible-failure sentinel, agent refuses to bind |
| 8 | SAFETY brief-opens + hidden landings = unknown → defaults stand (alarm > 2 s; uncalibrated codes shown as `code N`) |
| 9–10 | Owner delegates: Python agent on Windows (15), EMQX/NestJS/Kysely/dbmate/Redis (16), DRY_RUN permanent on real lifts (17), agent lives in WhizdomLift repo with dual-write + commit workflow (11), Alarm Center named **ศูนย์สัญญาณเตือน** everywhere (12), brand = text wordmark "The Whizdom" top-left + neutral camera stub (13), Design continues for frames 03/04/05 on the W fixture incl. demo-mode variants (14) |

**Still open (short):**
- **O1 Demo date** — sets which week the gate must close.
- **O2 Lift 4/5 board install dates** and W-03 reflash window (map fallback works meanwhile).
- **O3 FIRE / FIRE-RETURN activation test date** (whenever the lift team can — unblocks real fire alarms post-POC).
- **O4 PC #2 (Dell) spec check** — run `systeminfo` per §1; confirm Docker Desktop is permitted on it.

## 13. Kickoff prompts (two, in order)
**A — Gateway agent (in WhizdomLift repo, at the front-of-cabinet or Gateway machine):**
```
Read CLAUDE.md fully — its §4 safety rules and §6 lessons are binding. Then read
docs/backend/LMS_NG_Backend_Implementation_Plan_Whizdom_POC_v1_3.md §2 and §4. Build
lms_gateway_agent.py by extending log_lift.py: keep every existing duty
(lift-id guard, listen-only rts/dtr, reject counting, STOP_CAPTURE, fail-fast
then reconnect, capture_lift_N.log dual-write) and add: FW-banner port→lift
binding with --map fallback, per-pin debounce via lift_decode.debounce_pins,
decode to the §4.1 normalized model, sqlite-buffered MQTT publishing per §2.2
(topics/envelope from contracts/mqtt), and a --dry-run mode that prints the
would-be MQTT messages. Never write to the serial port. Prove it against
capture_lift_2.log replay before touching a live COM port.
```
**B — Backend vertical slice (in lms-ng repo, phase P2 of the workflow kit):**
```
Read docs/backend/LMS_NG_Backend_Implementation_Plan_Whizdom_POC_v1_3.md, then
contracts/mqtt/LMS_NG_MQTT_Topic_Specification_v1.yaml, contracts/openapi/LMS_NG_OpenAPI_v1.yaml
and database/migrations/0001_schema_v1.sql. Build the vertical slice exactly: docker-compose
(EMQX 5, Postgres 16, Redis 7, api, web, simulator), dbmate migrations + The Whizdom seeds (§6),
NestJS apps/api with IngestionModule (state path, dedupe, upsert, Redis fan-out), LivenessModule
(§5.2, real 90 s / sim 30 s), monitoring endpoints, and the WebSocket hub (§7.2). Generate JSON
Schemas for the §2.1 payloads into contracts/json-schema and reuse them in the simulator.
Definition of done: a replayed capture_lift_2.log stream, then the live Lift 2, reaches frame 02
within 2 s P95; INTERFACE_NO_RXTX / GATEWAY_OFFLINE transitions render correctly. Show me
docker-compose.yml, the ingestion module, and the WS envelope before building further.
```

## 14. Traceability additions
§2.1/§4 ← WhizdomLift `CLAUDE.md` §2–3/§6, `IODebug.ino` 1.2.2, `lift_decode.py`, `LIFT_STATUS.md`, `GATEWAY.md`, `TEST_REPORT_2026-08-08.md` (blind 14/14) · §5.2 thresholds ← firmware `HEARTBEAT_MS`/`IDENT_MS` + repo 75 s listen check · §5.4 ← MAX485 TX-only wiring + CLAUDE.md §4 rule 1.

*End of v1.3 — v1.0–v1.2 remain in the folder for diff.*
