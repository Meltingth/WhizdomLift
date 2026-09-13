# LMS-NG Claude Code Workflow Kit v1.0 — INSTALL (2026-09-03)
วิธีติดตั้ง (ทำในทั้งสอง repo: `lms-ng` และ `WhizdomLift`)
1. คัดลอกโฟลเดอร์ `.claude/`, `scripts/`, `docs/workflow/`, `WORKFLOW_STATE.md` ไปไว้ที่ root ของ repo
2. เปิด `CLAUDE.workflow.md` แล้วต่อท้ายเนื้อหาเข้าไปใน `CLAUDE.md` ของ repo (WhizdomLift มี CLAUDE.md อยู่แล้ว ห้ามแทนที่ ให้ต่อท้าย)
3. อัปเดต Claude Code ก่อนเริ่มทุกเฟส: `claude update`  (alias `fable/opus/sonnet` จะชี้รุ่นล่าสุดเอง)
4. เริ่มเซสชัน: `claude`  (settings.json ตั้ง model=fable + ultracode=true ให้แล้ว) หรือบังคับ `claude --model fable --effort ultracode`
5. ตรวจ: `/status` ต้องขึ้น Fable + ultracode · `claude plugin validate .claude/agents` ต้องไม่มี error
6. รัน `/phase P0` แล้วไล่ทีละเฟสตาม docs/workflow/PHASES.md
หมายเหตุ: อย่าตั้ง env `CLAUDE_CODE_EFFORT_LEVEL` (จะทับ effort ของ subagent และปิด ultracode) · บน Windows hooks ต้องเป็น PowerShell · Fable อาจใช้ usage credits และมี consent prompt ครั้งแรก
