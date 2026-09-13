# LMS-NG × Claude Code — Multi-Model Workflow Prompts v1.0
**Date:** 2026-09-03 · **Pairs with:** `claude_code_kit.zip` (drop-in `.claude/` kit) · Backend plan v1.3 §8 phases

---

## 0. How your 11 steps map to real Claude Code mechanics (verified against code.claude.com, 2026-09-01/02)

| Your step | Model + effort you asked for | How the kit does it | Native? |
|---|---|---|---|
| 1 Plan / refine / review the plan | Fable · Ultracode | The **lead session** runs `model: fable` + `"ultracode": true` (settings.json). Ultracode = xhigh reasoning + automatic dynamic workflows, so the lead fans big planning/review work out to parallel agents itself | ✅ |
| 2 Implement | Sonnet · Max | subagent `implementer-sonnet` — `model: sonnet`, `effort: max` | ✅ |
| 3 Deploy each phase to the test system | — | `scripts/deploy-phase.ps1` (docker compose + migrations + `/health` on the Dell; NSSM restart + publish check on the Gateway PC) | ✅ |
| 4 Opus reviews, finds bugs, writes test plan + test tools | Opus · Ultracode | subagent `reviewer-opus` — `model: opus`, `effort: max` (see note below) | ⚠ mapped |
| 5 Opus fixes what it found | Opus · Max | subagent `fixer-opus` — `effort: max` | ✅ |
| 6 Opus-level agent re-tests per Opus's plan | Opus · Max | subagent `verifier-opus` — read-only, `effort: max` | ✅ |
| 7 Fable advises + revises fix plan + test plan | Fable · Ultracode | the **lead** (Fable, ultracode) does it; or `fable-advisor` subagent (`effort: max`) for a fresh-context deep dive | ✅ |
| 8 Opus fixes per Fable's plan | Opus · Max | `fixer-opus` | ✅ |
| 9 Sonnet tests per Fable's plan | Sonnet · Max | `verifier-sonnet` — read-only, `effort: max` | ✅ |
| 10 Loop until done → commit + push | — | `/phase` command: max 4 cycles then stop; never commit red; `git push` | ✅ |
| 11 Next phase, repeat 1–9 | — | `/phase <next>` | ✅ |
| "Always the latest model; auto-adopt upgrades" | — | Only **aliases** (`fable`, `opus`, `sonnet`) are used — they resolve to the newest release of each family and are updated over time; `claude update` before each phase | ✅ |

**The one mapping you should know (steps 4 & 7):** `ultracode` is a *session* setting, not a per-agent effort level — subagent frontmatter accepts `low · medium · high · xhigh · max` only. Ultracode sends `xhigh` to the model; the kit gives the Opus reviewer `max` (one level deeper) and lets the lead's ultracode orchestration parallelize the review when it is large. If you ever want a *true* ultracode Opus session for a review, run it as a second terminal: `claude --model opus --effort ultracode` in the same repo and paste Prompt C2.

Other facts that shape the kit: `max` is session-only unless set by env var, so it lives in frontmatter (persistent per agent) · never set `CLAUDE_CODE_EFFORT_LEVEL` (overrides every subagent and disables ultracode orchestration) · Fable may bill usage credits and shows a one-time consent prompt · agent-teams split-pane needs tmux (not on Windows) — the kit uses subagents, which work everywhere · dynamic workflows are a research preview; if your org turns them off, `--effort ultracode` becomes plain `xhigh`.

---

## 1. Prompt A — Bootstrap (paste once per repo, in `claude` started at the repo root)

```
Read README.md of the workflow kit I just copied into this repo (files: .claude/settings.json,
.claude/agents/*.md, .claude/commands/phase.md, scripts/*.ps1, docs/workflow/PHASES.md,
WORKFLOW_STATE.md, CLAUDE.workflow.md). Then:
1. Append CLAUDE.workflow.md to CLAUDE.md (create CLAUDE.md if missing; in WhizdomLift append
   below the existing content and keep its §4 safety rules untouched).
2. Validate the kit: run `claude plugin validate .claude/agents`; fix any frontmatter it flags.
3. Confirm the effective configuration for me: which model this session runs on, whether ultracode
   is on, and the model+effort each subagent will use (read the frontmatter; do not pin model IDs anywhere).
4. Read docs/workflow/PHASES.md and the source plans in docs/ (Backend plan v1.3, UX Spec v1.2,
   contracts) and tell me whether any phase DoD is untestable in this repo as-is. Do not change scope.
5. Update WORKFLOW_STATE.md (phase P0, base commit) and stop. Do not start implementing.
```

Expected reply: session = Fable + ultracode; six subagents with `max`; any DoD gaps listed. If it reports a model other than Fable, run `/model fable` then `/effort ultracode` and re-check `/status`.

## 2. Prompt B — Run a phase (the everyday command)

```
/phase P1
```
That is the whole prompt. The command file carries the 11-step loop, gates, cycle cap, and commit rule. Optional argument to resume mid-loop after a manual fix: `/phase P2 --from 4`.

Plain-text fallback if you prefer not to use the command:
```
ultracode: run the LMS-NG phase loop for phase P2 exactly as defined in CLAUDE.md
("Multi-Model Workflow") and docs/workflow/PHASES.md. Delegate step 2 to @implementer-sonnet,
step 4 to @reviewer-opus, steps 5/8 to @fixer-opus, step 6 to @verifier-opus, step 9 to
@verifier-sonnet; deploy with scripts/deploy-phase.ps1 after every implementation or fix;
stop after 4 failed cycles; commit and push only when the DoD is green.
```

## 3. Prompt C — Interventions

**C1 — the loop stalled / hit the 4-cycle cap**
```
Summarize docs/workflow/logs/phase-<id>.md: what failed in each cycle, what was tried, and your
root-cause hypothesis. Then STOP and give me two options with costs: (a) re-plan the phase,
(b) narrow the DoD. Do not run more cycles until I choose.
```

**C2 — true ultracode Opus review in a second terminal** (`claude --model opus --effort ultracode`)
```
Act as reviewer-opus for phase <id> per .claude/agents/reviewer-opus.md, but run as a workflow:
parallel reviewers per module (ingestion, liveness, api, ws, ui), a merge step that dedupes findings,
and an independent verifier per BLOCKER. Write the test plan and tests/phase-<id>/run.ps1 as the
agent definition specifies. Do not modify production code.
```

**C3 — contract change request surfaced by a fixer**
```
A subagent reported that fixing <defect> requires a contract change (<which>). Do NOT change it yet.
Show me the smallest contract diff, the UI/backend blast radius, and an alternative that keeps the
contract. I will decide.
```

## 4. Prompt D — Model-upgrade check (run when Anthropic ships a new model)

Outside Claude Code: `claude update`. Then inside:
```
Report the models the aliases fable / opus / sonnet resolve to right now, and confirm every subagent
in .claude/agents still uses an alias (no pinned IDs). If a subagent's effort level is not supported by
the new model, tell me what Claude Code will fall back to.
```
(Claude Code falls back to the highest supported level at or below the one set.)

## 5. Operator checklist (Thai)
- ก่อนทุกเฟส: `claude update` → เปิด `claude` ใน repo → `/status` ต้องเป็น **Fable + ultracode** → `/phase <id>`
- ระหว่างรัน: `/tasks` ดู model+effort ของ subagent แต่ละตัว · `/workflows` ดู workflow ที่ ultracode สร้าง · Ctrl+T ดู task list
- ห้าม: ตั้ง `CLAUDE_CODE_EFFORT_LEVEL`, pin model ID, commit ตอนแดง, แก้ contract โดยไม่ผ่านคุณ
- เฟส P1 ทำใน repo **WhizdomLift** (กฎ CLAUDE.md §4 ของมันคือกฎเหล็ก); เฟสอื่นใน repo **lms-ng** บนเครื่อง Dell
- ค่าใช้จ่าย: Fable ultracode + subagent `max` คือโปรไฟล์แพงที่สุด — เหมาะกับงาน correctness-critical แบบนี้ แต่ให้ดู `/cost` หลังจบแต่ละเฟส
