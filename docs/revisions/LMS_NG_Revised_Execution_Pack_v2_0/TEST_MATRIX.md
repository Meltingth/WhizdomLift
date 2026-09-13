# TEST MATRIX — Revision v2.0

รายการทดสอบ **77 กรณี** เพื่อให้ Claude implement และเก็บ evidence; สถานะตั้งต้นทั้งหมด `NOT_RUN`. ตารางนี้ไม่ใช่รายงานว่าทดสอบโครงการจริงแล้ว.

ก่อน G-C ต้องผ่านทุกกรณีที่คอลัมน์ “ก่อน Canary” เป็น **ต้องผ่าน** ใน environment ที่ระบุ และต้องมี G-A/G-U ตามแผน. TEST fault injection ไม่อนุญาตให้ทำบน hardware จริง.

| ID | Phase | กรณี | Expected result | ก่อน Canary |
|---|---|---|---|---|
| C01 | A-DRAFT | Baseline inventory ไม่สูญ S2/S3 | พบ baseline ใน pack และ diff ทุก breaking field; ไม่อ้างว่าไม่มีทั่วระบบ | ต้องผ่าน |
| C02 | A-DRAFT | Python/Node schema parity | valid/invalid fixtures ให้ผลตรงกัน พร้อม format enforcement | ต้องผ่าน |
| C03 | A-DRAFT | Object closure / allOf | assembled valid payload ผ่าน; ฟิลด์เกินถูกปฏิเสธโดยไม่ reject body ที่ถูกต้อง | ต้องผ่าน |
| C04 | A-DRAFT | Int64 / ordering strings | เกิน JS safe integer ยัง compare ถูก; overflow ถูกปฏิเสธ | ต้องผ่าน |
| C05 | A-DRAFT | Envelope/topic/scope validation | UUID, realm, site, gateway, elevator, producer ผิดถูก reject | ต้องผ่าน |
| C06 | A-DRAFT | Pin/hash/release guard | รุ่นที่ pin ตรวจได้; latest ใหม่ไม่ทำลาย CI รุ่นเก่า; approval ไม่สร้างเอง | ต้องผ่าน |
| C07 | A-DRAFT | Floor seeds/evidence | Passenger 46 codes/43 landings; W05 code47→44 และ3..46 unknown | ต้องผ่าน |
| C08 | A-DRAFT | ACK/presence schema exceptions | LWT ไม่มี occurredAt ปลอม; ACK target/hash/type ถูกต้อง | ต้องผ่าน |
| G01 | P1-OFFLINE | ห้าม serial writes | AST/transitive audit + FakeSerial.write raises; tests ไม่เปิดพอร์ตจริง | ต้องผ่าน |
| G02 | P1-OFFLINE | Parser bounds/invalid garbage | 12/14 hex, malformed ms, oversize line/buffer ถูกจัดการแบบ bounded | ต้องผ่าน |
| G03 | P1-OFFLINE | Beacon/duplicate/wrong lift | LIFT0/unknown/duplicate refuse; ไม่มี current ผิดตัว | ต้องผ่าน |
| G04 | P1-OFFLINE | Ownership/PID reuse | PID/start time/executable/token และ port lock ป้องกัน double reader | ต้องผ่าน |
| G05 | P1-OFFLINE | Streaming debounce | Glitch/start/tail/timer/no-future-data ได้ state ที่นิยามไว้ | ต้องผ่าน |
| G06 | P1-OFFLINE | Board wrap/reboot/drift | wrap ไม่เป็น reboot; clock drift ไม่สร้าง false restart; discontinuity reset | ต้องผ่าน |
| G07 | P1-OFFLINE | Raw journal → outbox crash | recover source cursor ไม่ทำ record ซ้ำหรือข้าม durable source | ต้องผ่าน |
| G08 | P1-OFFLINE | Known-good independent runtime | baseline logger import/run ได้โดยไม่มี agent modules/environment ใหม่ | ต้องผ่าน |
| G09 | P1-OFFLINE | Shadow/replay isolation | ไม่มี source log writes/COM open; TEST IDs; date ambiguity มี quality | ต้องผ่าน |
| G10 | P1-OFFLINE | Worker/network failure isolation | Publisher stall ไม่บัง reader; health แยก Capture/Delivery | ต้องผ่าน |
| G11 | P1-OFFLINE | Freshness cadence/boundaries | idle60sไม่stale; valid frame75/90ชัด; garbage/heartbeatไม่refresh ST | ต้องผ่าน |
| G12 | P1-OFFLINE | Direction/status conflict | UP+DN และ RUNNING conflict เป็น UNKNOWN/quality; ไม่เดาตำแหน่ง | ต้องผ่าน |
| G13 | P1-OFFLINE | Sensor suspicion validation | VS2 8/4 ไม่ยืนยัน fault โดยไม่มี independent evidence; odd glitch ไม่แก้เอง | ต้องผ่าน |
| G14 | P1-OFFLINE | Expected absent/migrating lift | W04ไม่ fail ทั้ง fleet; new beacon ไม่ auto-commission | ต้องผ่าน |
| G15 | P1-OFFLINE | Timestamp compatibility | Format/CLI และ latency ที่ตั้งใจเปลี่ยนทดสอบแยก; ไม่มี byte-identical claim เท็จ | ต้องผ่าน |
| I01 | P2-TEST | PUBACK only | Outbox ยังไม่ DB_COMMITTED แม้ได้รับ PUBACK | ต้องผ่าน |
| I02 | P2-TEST | Application ACK success/lost | ACKหลังSQLcommit; lostACK→retry→one business effect+ACKซ้ำ | ต้องผ่าน |
| I03 | P2-TEST | API-only outage | Brokerอยู่/APIดับ:durable recordsกลับเข้าDBครบหลังrecovery | ต้องผ่าน |
| I04 | P2-TEST | Database-only outage | ไม่มีsuccessACKก่อนDBพร้อม; replayครบหลังDBกลับ | ต้องผ่าน |
| I05 | P2-TEST | Broker outage/restart | RawCapture/SQLiteเดินต่อ; queue drain ภายใต้bounds | ต้องผ่าน |
| I06 | P2-TEST | Crash before transaction commit | Receipt/domain rollbackทั้งชุด; retryทำสำเร็จครั้งเดียว | ต้องผ่าน |
| I07 | P2-TEST | Crash after commit before ACK/fanout | receiptให้ACKซ้ำ; server outboxส่งUI/alarmต่อ | ต้องผ่าน |
| I08 | P2-TEST | Payload mismatch under same identity | quarantine/hashconflict; ไม่แก้ข้อมูลเดิมหรือsuccessACK | ต้องผ่าน |
| I09 | P2-TEST | Fair fresh/backlog scheduling | freshไม่รอhistoryทั้งหมด; historyและทุกliftไม่starve | ต้องผ่าน |
| I10 | P2-TEST | Retained old snapshot | Backlogไม่ทับBrokerretained; DBcurrentไม่ถอย | ต้องผ่าน |
| I11 | P2-TEST | Inbox dedupe across partitions | Same ID eventTimeเปลี่ยนเป็นconflict; ไม่มีduplicateglobal | ต้องผ่าน |
| I12 | P2-TEST | Poison record / ACK spoof | Quarantineไม่บังรายการอื่น; ACKคนอื่นล้างqueueไม่ได้ | ต้องผ่าน |
| O01 | P2-TEST | Process restart with queued history | identity/bootIdของrecordเก่าคงเดิม; durable seqของใหม่เพิ่มต่อ | ต้องผ่าน |
| O02 | P2-TEST | Wall clock moves backwards/forwards | currentไม่ตัดสินจากwallclock; TIME_UNCERTAIN/latencyrefusalถูกต้อง | ต้องผ่าน |
| O03 | P2-TEST | SQLite lost/old restored/producer copied | No seq reset under old epoch; unauthorized producer cannot own current | ต้องผ่าน |
| O04 | P2-TEST | WS snapshot/delta race | ไม่มีdeltaตกหล่นจากbootstrap; per-asset revisionsถูกต้อง | ต้องผ่าน |
| O05 | P2-TEST | Redis/WS/server restart/drop-last-delta | resnapshot/revision heartbeatทำให้clientคืนconsistentstate | ต้องผ่าน |
| O06 | P2-TEST | New connection with old will | LWTเก่าไม่ล้มconnectionใหม่; retainedONLINEต้องfreshproof | ต้องผ่าน |
| U01 | HUD-CORE | Shaft motion tied to state | เปลี่ยนAPIstateแล้วcar/เลขชั้นอัปเดต ไม่ใช้routeจำลอง | ต้องผ่าน |
| U02 | HUD-CORE | No new source data | ไม่สร้างfloorถัดไป/ปลายทางจากUPเอง | ต้องผ่าน |
| U03 | HUD-CORE | Disconnected/unknown/conflict | หยุดprojection; lastknown/age/qualityอ่านชัด | ต้องผ่าน |
| U04 | HUD-CORE | Service lift raw scale | W05uncalibratedไม่วางตรงphysicalfloorที่เดา | ต้องผ่าน |
| U05 | HUD-CORE | W04 service vs commissioning | outofserviceไม่กลายเป็นรอติดตั้ง; KPIdenominatorถูก | ต้องผ่าน |
| U06 | HUD-CORE | Alarm & labels while animating | alarm/confirmedfloorไม่รอanimationจบ; missingFIREไม่เป็นNORMAL | ต้องผ่าน |
| U07 | HUD-CORE | Tab/reconnect/reduced motion | resumeจากsnapshot; noqueuedobsoleteanimations; motionลดได้ | ต้องผ่าน |
| U08 | HUD-CORE | Steady latency / clocks | ≥200samples P95≤2s Gatewayreceipt→UIcommit; clocksตรวจครบ | ต้องผ่าน |
| U09 | HUD-CORE | HUD core FPS/screens | 1080p5cars/4charts P95frame≤33.3ms target; nooverlap1366/4K | ต้องผ่าน |
| U10 | P3-HISTORY | Analytics/censored/coverage | definitiongroundtruthผ่าน; unknown≠0; backlogไม่ยิงlivealarm | ภายหลัง/Field gate |
| U11 | P5-PRESENTATION | Presentation reference fidelity | ownerตรวจOperations/Presentationภาพอ้างอิง; ไม่ใช้PNGทั้งภาพแทนUI | ภายหลัง/Field gate |
| U12 | HUD-CORE | 2h pre-canary memory soak | boundedbuffers/listeners; ไม่มีunexplainedmemorygrowth | ต้องผ่าน |
| S01 | P2-TEST | REAL/TEST topic ACL | simเขียนREAL/gatewayอื่น/ACKไม่ได้; Server subscriptionsครอบTESTที่อนุญาต | ต้องผ่าน |
| S02 | P2-TEST | REST/WS auth and scope | anonymous/expiredsession/wrongsiteถูกปฏิเสธ; Originverified | ต้องผ่าน |
| S03 | P2-TEST | TLS/cert/credentials | invalidCA/hostnameปฏิเสธ; ไม่มีdefaultsharedpassword; no1883LAN | ต้องผ่าน |
| S04 | P2-TEST | Public artifact secret scan | ไม่มีprivatekey/password/rawoperationalcapture/realhostconfigในpublicdiff | ต้องผ่าน |
| S05 | P2-TEST | Read-only command enforcement | REAL LIVEdeniedทุกrole; Agentไม่มีhardwaredispatch | ต้องผ่าน |
| D01 | P2-TEST | TEST routing end-to-end | SIDsจากlms-simเข้าTESTDB/current/WSได้ตามscope | ต้องผ่าน |
| D02 | P4-ALARMS-DEMO | Demo per-session isolation | Demoผู้ใช้หนึ่งคนไม่เปลี่ยนLiveผู้ใช้อื่นหรือingestion | ภายหลัง/Field gate |
| D03 | P4-ALARMS-DEMO | Demo zero contamination | REALtelemetry/alarm/commandrowsไม่เพิ่มจากDemo; auditstart/stopอนุญาต | ภายหลัง/Field gate |
| D04 | P4-ALARMS-DEMO | Exit Demo / live monitoring | กลับsnapshotสด; positionsจำลองไม่ปน; realalarmเดินต่อ | ภายหลัง/Field gate |
| P01 | P2-TEST | Fresh/upgrade migrations | ไม่rewriteappliedmigration; scratchfresh+upgradeทั้งคู่ผ่าน | ต้องผ่าน |
| P02 | P2-TEST | Partition boundary/history | ข้ามเดือน/ปี/lateeventได้; futuretimestampไม่สร้างpartitionไม่จำกัด | ต้องผ่าน |
| P03 | P2-TEST | Backup restore and reconciliation | serverDataEpochเปลี่ยนตามrunbook; archivedrecordsreconcile; currentไม่ถอย | ต้องผ่าน |
| P04 | P2-TEST | Outbox/storage pressure | boundedcapacity+72h/2×ratecalculation; no silent unacked drop; scratchfull-disk | ต้องผ่าน |
| P05 | P2-TEST | Build without submodule | lms-ngcloneเดี่ยวbuild/testได้จากpinnedcontract/fixture | ต้องผ่าน |
| P06 | P2-TEST | Dell cold boot readiness | serviceขึ้นตามhostingที่อนุมัติ; ไม่ต้องauto-loginadminโดยไม่ยอมรับrisk | ต้องผ่าน |
| P07 | P2-TEST | Release rollback rehearsal | immutableoldruntime/configคืนCaptureในbudgetที่วัด; noimportnewmodules | ต้องผ่าน |
| P08 | P6-HARDENING | Full24hsoak/restore/security | รายงานCPU/RAM/disk/queue/versionsและknownrisksพร้อมhandover | ภายหลัง/Field gate |
| P09 | P2-TEST | Capacity/load multiple clients | TESTload≥2×measuredaverageพร้อมburstและหลายbrowser; rate/bytesสมมุติฐานชัด | ต้องผ่าน |
| P10 | P2-TEST | Workflow/gates do not self-approve | -PlanOnlydefault; missing/expired/wrongscopetokenblock; noautoall-liftcutover | ต้องผ่าน |
| F01 | P2-CANARY | One-lift authorization/identity | ownerrecordตรงwindow/release/lift; verifiedboard; portไม่ซ้ำ | ภายหลัง/Field gate |
| F02 | P2-CANARY | Actual floor/shaft/capture continuity | selectedliftตรงfieldobservation; otherloggers/countersยังเดิน | ภายหลัง/Field gate |
| F03 | P2-CANARY | Canary observation/evidence | target2h/20tripsเมื่อเกิดได้จริง; gapsเปิดเผย; nofalsePASS | ภายหลัง/Field gate |
| F04 | P2-CANARY | Field rollback if approved | known-goodคืนตามtarget; preservequeue/historyและบันทึกgap | ภายหลัง/Field gate |
| F05 | P3-FLEET | Sequential fleet rollout | eachliftapproved; W05profileเฉพาะ; W04notautoenrolled | ภายหลัง/Field gate |

## เกณฑ์บันทึกผล

แต่ละ test ต้องมี assertion, input fixture/hash, environment, sourceMode, commit/contractHash, result, artifact path และเวลาที่รันจริง. Skipped/ไม่มีเครื่อง = NOT_RUN/BLOCKED ไม่ใช่ PASS. ดูแม่แบบ `templates/PHASE_REPORT_TEMPLATE.md`.

การอนุมัติยกเว้นเฉพาะกรณีต้องเป็น ACCEPTED_RISK ที่มี owner/scope/expiry ไม่เปลี่ยนค่า test เป็น PASS และไม่ยกเว้น read-only, identity, authorization, non-contamination หรือ immutable rollback safety โดยไม่แก้ขอบเขตโครงการอย่างชัดแจ้ง.
