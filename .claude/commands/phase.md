---
description: Run the LMS-NG multi-model phase loop (plan -> implement -> deploy -> review/test -> fix -> verify -> escalate -> commit) for one phase
argument-hint: <phase-id e.g. P1> [--from step]
---

ultracode: Run the LMS-NG phase loop for phase **$ARGUMENTS** exactly as defined in CLAUDE.md
("Multi-Model Workflow") and docs/workflow/PHASES.md. You are the lead (Fable, ultracode on).
Keep your own context lean: delegate every step below to the named subagent with a full,
self-contained delegation prompt (the subagent sees nothing of this conversation).

PRE-FLIGHT
- Read docs/workflow/PHASES.md (scope + Definition of Done for $ARGUMENTS) and WORKFLOW_STATE.md.
- Record phase start in WORKFLOW_STATE.md (phase, git base commit, cycle=0).
- Confirm the tree is clean (git status). If not, stop and ask the human.

STEP 1 - PLAN (lead, yourself)
- Write docs/workflow/plans/phase-$ARGUMENTS.md: scope, architecture decisions, files to create/change,
  contracts touched (must stay unchanged), test strategy, DoD checklist copied from PHASES.md, risks.
- Review your own plan against the source documents in docs/ (Backend plan, UX spec, contracts). Fix gaps.

STEP 2 - IMPLEMENT -> delegate to @implementer-sonnet
- Delegation prompt must include: plan path, DoD, repo run/test commands, the contracts list, and
  "do not commit". Wait for its report.

STEP 3 - DEPLOY
- Run: pwsh ./scripts/deploy-phase.ps1 -Phase $ARGUMENTS   (builds/starts the test system, runs smoke checks)
- If deploy fails, delegate the failure to @fixer-opus and redeploy (counts as a cycle).

STEP 4 - REVIEW + TEST PLAN + TOOLS -> delegate to @reviewer-opus
- Delegation prompt: plan path, base commit, deploy URLs/ports, DoD. It writes the test plan + tests/phase-$ARGUMENTS/run.ps1 and gives PASS/FAIL.

STEP 5 - FIX -> delegate to @fixer-opus (only if step 4 = FAIL)
- Pass the defect list location. Redeploy (step 3) after fixes.

STEP 6 - VERIFY -> delegate to @verifier-opus
- It re-runs the reviewer test plan. PASS -> go to STEP 10.

STEP 7 - ESCALATE (only if step 6 = FAIL)
- Yourself: diagnose from docs/workflow/logs/phase-$ARGUMENTS.md; write phase-$ARGUMENTS-fixplan-N.md and
  testplan-vN.md. If your context is heavy or two escalations already happened, delegate the diagnosis to
  @fable-advisor instead and adopt its plans.

STEP 8 - FIX PER PLAN -> delegate to @fixer-opus with the fix plan path. Redeploy.

STEP 9 - VERIFY PER PLAN -> delegate to @verifier-sonnet with the revised test plan path.

STEP 10 - LOOP / COMPLETE
- FAIL -> increment cycle; if cycle >= 4, STOP and report to the human with the log summary (do not keep burning).
- PASS -> mark every DoD item in WORKFLOW_STATE.md, then commit and push:
  git add -A && git commit -m "feat(phase-$ARGUMENTS): <one-line summary> [workflow: lead=fable, impl=sonnet, review/fix=opus]" && git push
  Never commit a red tree. Never force-push.

STEP 11 - HAND-OFF
- Append the phase summary to docs/workflow/logs/phase-$ARGUMENTS.md and print: phase, cycles used,
  defects found/fixed, test counts, and the next phase id from PHASES.md. Then stop and wait for the human
  to run /phase <next>.
