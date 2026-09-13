# AGENTS.md — WhizdomLift Edge / Gateway Operating Rules

## 0. Purpose

This file defines the mandatory operating rules for Codex when working inside the `WhizdomLift` repository.

These rules apply to all files under this repository unless a deeper `AGENTS.md` explicitly defines more specific rules.

This repository is the **Edge / Gateway / Capture** side of the LMS-NG / WhizdomLift system.

The project uses a controlled multi-agent workflow:

- **Project Owner** — final human authority.
- **System Architect / Technical Lead** — ChatGPT; defines architecture, phases, corrections, acceptance criteria, and recommends gate decisions.
- **Claude Code** — primary Backend / Edge / Infrastructure implementer.
- **Codex** — independent QA/Audit engineer and primary Frontend HUD implementer.

Codex MUST NOT assume the role of System Architect or Gate Owner.

---

# 1. Repository Identity

Canonical repository:

```text
Repository:
WhizdomLift

GitHub:
https://github.com/Meltingth/WhizdomLift.git
```

Expected `origin`:

```text
https://github.com/Meltingth/WhizdomLift.git
```

Before any commit or push:

```powershell
git remote -v
git remote get-url origin
```

If `origin` does not match the expected repository:

```text
STOP_PUSH
REMOTE_MISMATCH
```

Do not silently rewrite the remote.

---

# 2. Environment Map

## 2.1 Development workstation

Development path:

```text
C:\NST\Software Dev\WhizdomLift
```

Normal development, audit and offline testing should occur here.

Typical allowed DEV work:

```text
source inspection
offline decoder tests
fixture tests
contract verification
audit tooling
replay tooling
documentation
non-live Gateway Agent development
safe unit/integration tests
```

---

## 2.2 Production Dell

Production/runtime path:

```text
D:\WhizdomLift
```

This is a runtime/deployment repository.

It is NOT the normal coding workspace.

Normal code development must not originate from this path.

---

## 2.3 Related LMS-NG repository

DEV:

```text
C:\NST\Software Dev\lms-ng
```

Production Dell:

```text
D:\lms-ng
```

GitHub:

```text
https://github.com/Meltingth/lms-ng.git
```

Repository responsibilities must remain separated:

```text
WhizdomLift
= Edge / Capture / Serial / Decoder / Gateway Publisher

lms-ng
= Platform / Backend / Web / Contracts / Database / Infrastructure
```

Do not merge the repositories.

Do not introduce a mandatory Git submodule unless explicitly authorized.

---

# 3. Environment Identity Check

Never infer DEV or Production from drive letter alone.

Before any environment-sensitive action verify:

```powershell
hostname
Get-Location
git remote -v
git branch --show-current
git rev-parse HEAD
git status --short
```

Classify the environment:

```text
DEV
PRODUCTION_DELL
UNKNOWN
```

If identity is unclear:

```text
STOP
ENVIRONMENT_IDENTITY_BLOCKED
```

---

# 4. Path Portability

Portable source code and tests must not hard-code either environment path.

Forbidden in portable logic:

```text
C:\NST\Software Dev\WhizdomLift
D:\WhizdomLift
C:\NST\Software Dev\lms-ng
D:\lms-ng
```

Prefer:

```text
repository-relative paths
CLI arguments
environment variables
configuration files
script-directory discovery
```

PowerShell example:

```powershell
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
```

Python example:

```python
repo_root = Path(__file__).resolve().parents[1]
```

Absolute paths are allowed only in:

```text
deployment documentation
machine-local configuration
private inventory/evidence
explicit operator commands
```

---

# 5. Authority and Gate Rules

Codex cannot independently approve or open any project gate.

Project gates:

```text
G-A  Contract approval
G-U  HUD / UX/UI approval
G-C  Live canary approval
G-R  Fleet rollout approval
G-H  Final field acceptance
```

Only the Project Owner may approve a gate after System Architect review.

A passing test does not open a gate.

Allowed statuses:

```text
PASS
FAIL
BLOCKED
NOT_RUN
```

Codex MUST NOT independently declare:

```text
APPROVED
PRODUCTION_READY
FIELD_ACCEPTED
```

---

# 6. WhizdomLift Responsibility Boundary

This repository owns:

```text
Serial / RS485 capture
board identity handling
raw signal logging
raw signal decoding
debounce / quality handling
local Edge/Gateway state
Gateway Agent
local durable Edge outbox
MQTT publishing from Edge
application ACK handling on Edge
offline replay/shadow support
Capture monitoring / watchdog integration
```

This repository does NOT own:

```text
Backend floor labels
REST API
WebSocket server
PostgreSQL business storage
Redis
EMQX server configuration ownership
Frontend HUD presentation
Alarm business rules
analytics definitions
```

Those belong to `lms-ng`.

---

# 7. Floor Mapping Ownership

WhizdomLift publishes raw/normalized Edge facts.

It must not become the authoritative owner of display floor labels.

Allowed Edge fields include:

```text
floorRaw
position code
RUNNING
SAFETY
UP
DN
signal quality
capture identity
decoder version
```

Backend owns:

```text
floorDisplay
floorKind
floorProfileVersion
displayAnchor
```

Do not implement global display formulas such as:

```text
floor = floorRaw - 2
```

W-05 currently known mapping is:

```text
1  → B1
2  → 1
47 → 44
```

Codes:

```text
3..46
```

remain uncalibrated until authoritative Backend mapping exists.

---

# 8. Read-Only Elevator Safety Principle

WhizdomLift is a monitoring/capture system.

Without explicit live authorization, Codex MUST NOT introduce or activate any capability that writes commands back to the elevator controller.

Forbidden:

```text
serial transmit to elevator control
relay output actuation
remote call commands
door commands
bypass commands
safety overrides
write-enabled protocol behavior
```

Any unexpected transmit path is a critical finding.

---

# 9. COM / Serial Safety

Without explicit G-C or equivalent live authorization, Codex MUST NOT:

```text
open a real COM port
probe COM ports actively
write serial data
steal a COM port from running Capture
restart a serial session
change baudrate/runtime configuration on Production
```

Offline tests must use:

```text
recorded fixtures
fake serial devices
mock streams
sanitized logs
simulators
```

If a test requires real COM access:

```text
BLOCKED
WAIT_FOR_ARCHITECT
```

---

# 10. Capture Safety

The running Capture system is a production lifeline.

Codex MUST NOT, without explicit authorization:

```text
stop Capture
restart Capture
kill Capture processes
modify deployed Capture arguments
modify deployed logger behavior
replace the active Python runtime
change the active vendor dependency directory
change Capture startup order
```

No test is allowed to stop real Capture merely to prove recovery.

---

# 11. Deployed log_lift.py Protection

The deployed `log_lift.py` is treated as known-good until a controlled migration phase explicitly replaces it.

Without explicit authorization, Codex MUST NOT:

```text
refactor deployed log_lift.py
modify deployed log_lift.py
change its CLI behavior
change its log format
change its stop behavior
change its COM ownership behavior
```

If a new Agent needs different behavior, build it separately first.

Rollback must remain independent from new Agent modules.

---

# 12. STOP_CAPTURE Rule

The existing global `STOP_CAPTURE` mechanism affects all running lift loggers sharing the deployment directory.

It must NOT be used for a single-lift canary.

Until a verified per-lift ownership/hold mechanism exists:

```text
P2-CANARY = BLOCKED
```

Any per-lift stop/hold mechanism must be implemented at the approved launcher/control-plane layer rather than by silently changing the known-good logger.

---

# 13. Scheduled Task Protection

Without explicit production authorization, Codex MUST NOT:

```text
create Scheduled Tasks
delete Scheduled Tasks
disable Scheduled Tasks
change triggers
change action commands
change execution user
change startup cadence
change watchdog cadence
```

Inspection may be read-only.

If a future per-lift HOLD mechanism is implemented, it must be tested offline first and must not allow the Scheduled Task to automatically restart the lift logger currently handed to Canary.

---

# 14. Firmware Safety

Without explicit firmware authorization, Codex MUST NOT:

```text
flash Arduino
modify firmware on Production
change pinMode
change INPUT to OUTPUT
change relay polarity
change debounce at firmware level
change beacon identity
```

Firmware changes require:

```text
separate scope
separate test evidence
separate authorization
```

---

# 15. Board Identity Rule

Never trust COM port number alone as elevator identity.

Identity must use verified board/lift beacon or approved equivalent identity mechanism.

Do not assume:

```text
COM3 = Lift 1 forever
```

Port reassignment after reboot must not cause lift identity swaps.

---

# 16. Contract Boundary

`lms-ng` is the source repository for current LMS-NG Contract definitions.

WhizdomLift receives a pinned vendored copy.

The relationship is:

```text
lms-ng Contract release
        ↓
version + commit + tree hash
        ↓
WhizdomLift vendored Contract copy
```

WhizdomLift MUST NOT silently modify vendored Contract bytes.

Use approved synchronization tooling.

If a Contract mismatch occurs:

```text
BLOCK
do not hand-edit the vendored copy
report candidate/version/hash mismatch
```

---

# 17. Frozen Contract Safety

When a Contract candidate is frozen:

Codex must not modify:

```text
contracts/
contract manifests
MQTT schema
OpenAPI-derived Edge expectations
enum metadata
vendored contract copy
```

unless authorized to create a new candidate.

If a defect is found:

```text
FAIL or BLOCKED
record evidence
request Architect decision
```

Do not silently repair frozen bytes.

---

# 18. Git Branch Rules

Never perform normal development directly on `main`.

Recommended Codex audit branch:

```text
codex/audit-<phase>-<claude-sha>
```

Recommended safe Edge development branch:

```text
codex/edge-<purpose>
```

Claude branches remain Claude-owned.

Before editing:

```powershell
git status
git branch --show-current
git log -1 --oneline
git remote -v
```

Do not overwrite unrelated user work.

---

# 19. Git Operations Prohibited Without Authorization

Do not run:

```text
git reset --hard
git clean -fd
git push --force
git push --force-with-lease
git filter-repo
git filter-branch
```

Do not rewrite shared history merely to make it clean.

Do not delete branches without explicit instruction.

---

# 20. Mandatory Commit and Push Workflow

Every completed atomic change set MUST follow:

```text
edit
→ validate
→ test
→ inspect diff
→ secret/log scan
→ commit
→ push
→ verify upstream
```

Atomic change examples:

```text
add offline decoder test
add safe audit harness
fix replay ordering test
document Gateway identity rule
add sanitized fixture
```

Do not commit every keystroke.

But once one logical change is complete, commit and push it before starting unrelated work.

---

# 21. Commit Message Convention

Use meaningful Conventional Commit-style messages.

Examples:

```text
test(edge): add board identity replay coverage
fix(edge): preserve retry message identity
docs(edge): document canary ownership requirements
test(audit): add exact-sha WhizdomLift review harness
```

Avoid:

```text
update
fix stuff
changes
final
work
```

---

# 22. Push Destination

DEV repository:

```text
C:\NST\Software Dev\WhizdomLift
```

must push to:

```text
https://github.com/Meltingth/WhizdomLift.git
```

Production Dell repository:

```text
D:\WhizdomLift
```

must also point to the same GitHub repository.

Before push:

```powershell
git remote get-url origin
```

Mismatch:

```text
STOP_PUSH
REMOTE_MISMATCH
```

---

# 23. Production Dell Commit Rule

Normal development commits MUST NOT originate from:

```text
D:\WhizdomLift
```

Normal flow:

```text
DEV
→ commit
→ push GitHub
→ audit
→ Architect review
→ approved release
→ deploy exact SHA to Dell
```

Dell must not become a separate source of truth.

Emergency production fixes require explicit authorization and must be pushed back to GitHub immediately.

---

# 24. No Uncommitted Source Changes at Task End

Before task completion:

```powershell
git status --short
```

Completed source changes must be committed.

If completed source changes remain uncommitted:

```text
TASK_NOT_COMPLETE
```

Explain any intentional local-only files.

---

# 25. Operational Logs

Never automatically commit or push continuing live runtime data:

```text
capture_lift_*.log
capture_launcher.log
*.pid
live telemetry dumps
raw runtime diagnostics
```

Do not delete local runtime logs merely because they are excluded from commits.

If Git already tracks them:

- do not include new log growth in normal feature commits;
- do not rewrite public history without authorization;
- report the condition.

---

# 26. Sanitized Fixtures

Testing should use:

```text
tests/fixtures/
```

with deterministic sanitized data.

Examples:

```text
normal_idle.log
normal_trip.log
relay_bounce.log
board_restart.log
link_lost.log
malformed_frame.log
identity_change.log
clock_wrap.log
```

Fixtures must not contain secrets or unnecessary operational history.

---

# 27. Secret and Data Scan Before Commit

Before every commit inspect:

```powershell
git diff
git diff --cached
git status --short
```

Check for:

```text
password
secret
token
API key
private key
bearer token
connection string
SSH credential
certificate private key
real customer information
raw operational telemetry
private task exports
machine-local secrets
```

If found:

```text
STOP
DO_NOT_COMMIT
```

---

# 28. Testing Before Commit

Run all applicable tests before commit.

For Python changes:

```text
targeted pytest
full applicable pytest suite
static validation where configured
```

For PowerShell scripts:

```text
PlanOnly / dry-run mode where supported
fixture-based tests
parameter/path validation
```

Do not use a dry-run as proof that a side-effecting command itself works.

If a real external dependency is unavailable:

```text
BLOCKED
or
NOT_RUN
```

---

# 29. Testing After Commit

After commit:

```powershell
git status
git show --stat --oneline HEAD
```

For critical changes rerun the relevant targeted test against committed HEAD.

---

# 30. Audit Independence

When auditing Claude Code:

Use the exact Claude commit SHA and exact comparison-base SHA.

Record:

```text
ClaudeCommit
ComparisonBase
ContractVersion
ContractHash
AuditBranch
AuditCommit
```

Never audit an arbitrary current working tree if it differs from the supplied SHA.

If the exact commit cannot be obtained:

```text
BLOCKED
```

---

# 31. No Silent Fixes During Audit

If Codex finds a defect in Claude-owned code while auditing:

Do not silently patch production logic.

Document:

```text
Finding
Severity
Evidence
Reproduction
Expected
Actual
SuggestedFix
```

Then:

```text
FAIL
WAIT_FOR_ARCHITECT
```

The Architect determines who fixes it.

---

# 32. Audit Report Location

Store audit reports under:

```text
docs/audit/AUDIT_<PHASE>_<CLAUDE_SHA>.md
```

Each report includes:

```text
AUDIT_RESULT
PASS count
FAIL count
BLOCKED count
NOT_RUN count
Critical findings
Major findings
Minor findings
Evidence paths
Regression risk
Deployment recommendation
NextAllowedAction
```

---

# 33. Capture Health Evidence

When authorized to inspect Production health, prefer non-invasive evidence:

```text
existing log growth
pid ownership
capture_status.py
board identity lines
existing launcher logs
```

Do not open another COM handle just to verify Capture.

`/health` style process checks do not prove lift telemetry is fresh.

---

# 34. Freshness Semantics

Edge and UI semantics must remain consistent with the Revised Plan.

REAL field transport:

```text
valid frame age < 75s      → OK
75s <= age < 90s           → AGING
age >= 90s                 → NO_RXTX
```

REAL source state:

```text
valid ST age < 90s         → VALID
age >= 90s                 → STALE
```

Gateway heartbeat:

```text
age < 30s                  → ONLINE
age >= 30s                 → OFFLINE
```

Do not allow:

```text
Agent heartbeat
```

to refresh:

```text
lastValidStateAt
```

Identity traffic alone must not make stale lift state fresh.

---

# 35. Time Handling

Use monotonic time for:

```text
timeouts
debounce timers
freshness ages
retry timers
```

Use wall clock for:

```text
recorded timestamps
operator display
history
```

Wall-clock rollback must not reorder live state.

Clock uncertainty must remain visible in provenance.

---

# 36. Durable Message Identity

Future Gateway Agent behavior must preserve message identity across retry.

A retry must not silently create a new logical event.

Durable identity fields include the approved Contract fields such as:

```text
messageId
producerId
producerEpoch
streamId
streamSeq
sourceRef
payloadHash
```

PUBACK does not mean database durability.

Application ACK after Backend DB commit is required for DB-committed status.

---

# 37. Outbox Safety

When the future Edge outbox exists:

Never delete a durable message solely because MQTT transport PUBACK arrived.

Expected state concept:

```text
PENDING
→ TRANSPORT_ACKED
→ DB_COMMITTED
```

Messages remain recoverable until valid application ACK confirms durable Backend commit.

---

# 38. Replay / Backlog Rules

Backlog replay must not overwrite newer current state.

Fresh state must not remain blocked behind a long historical queue.

Historical retry:

- preserves original identity;
- preserves original observed time;
- remains LIVE if it originated LIVE;
- does not refresh source freshness;
- does not create duplicate business effects.

---

# 39. REAL / TEST Isolation

WhizdomLift real Gateway publisher must never publish into TEST identity by accident.

TEST tools must never publish to REAL IDs/topics.

Simulation tools should refuse real `W-*` targets unless explicitly designed and authorized for a non-publishing validation path.

No test should rely only on UI labels to distinguish REAL vs TEST.

---

# 40. Dependency Changes

For dependency updates:

1. explain purpose;
2. pin version;
3. update lock/requirements;
4. test import/runtime;
5. run security/dependency checks;
6. avoid unrelated upgrades.

Do not replace the Production Python runtime merely for convenience.

---

# 41. Vendor Dependencies

The known-good Capture environment currently relies on vendored dependencies.

Do not assume user-profile `site-packages` are visible to Scheduled Task processes.

New Edge tooling must be reproducible from its own declared dependency set.

Do not remove known-good `vendor/` dependencies without explicit migration proof.

---

# 42. Launcher / Watchdog Rules

Launcher/watchdog tooling must report what it actually did.

A command exiting with code 0 is not sufficient proof.

Report evidence such as:

```text
identity discovered
process started
PID verified
log growth observed
board beacon observed
capture remained alive after verification delay
```

Do not rely on `-WhatIf` to prove a side-effecting production action works.

---

# 43. Canary Requirements

Before G-C can be approved, a single-lift Canary handover must support:

```text
HOLD exactly one lift
verify logger PID ownership
prevent Scheduled Task from restarting held logger
keep other lifts capturing
start Canary Agent only after COM release
rollback to known-good independent logger
verify rollback health
record actual capture gap
```

Global `STOP_CAPTURE` is not acceptable for a single-lift Canary.

---

# 44. Known-Good Rollback

Rollback must target a known-good release independent of new Agent modules.

Rollback evidence must include:

```text
known-good commit
file hashes
Python runtime/dependencies
launcher command
expected identity
capture health verification
```

Do not call rollback successful merely because a process started.

Verify actual data resumes.

---

# 45. Deployment Workflow

Normal development:

```text
C:\NST\Software Dev\WhizdomLift
        ↓
feature/audit branch
        ↓
tests
        ↓
commit
        ↓
push GitHub
        ↓
Codex/Architect review
        ↓
approved release
        ↓
SSH Dell
        ↓
D:\WhizdomLift
        ↓
fetch exact approved SHA
        ↓
deploy
        ↓
verify Capture
```

---

# 46. Deployment Candidate

Before any Dell deployment create or verify a deployment record containing:

```text
repository
remoteUrl
sourceBranch
sourceCommit
contractVersion
contractHash
GatewayAgentVersion
testSummary
auditSummary
rollbackRelease
targetHost
targetPath
```

Then STOP for deployment authorization.

---

# 47. SSH Production Safety

When SSH access is authorized:

Begin read-only.

Verify:

```text
hostname
OS
network
repo path
remote
branch
SHA
git status
Python runtime
running Capture processes
Scheduled Task state
disk
logs
available ports
```

Do not assume Production matches DEV.

Never automatically:

```text
delete logs
kill all Python processes
change firewall
change hostname
remove Scheduled Tasks
replace Python
reformat storage
```

---

# 48. Deployment by Exact SHA

Production deployment must use an approved exact commit/tag.

Do not deploy with vague instructions such as:

```text
git pull latest
```

without explicit authorization.

Record:

```text
previousSHA
deployedSHA
time
rollbackSHA
health before
health after
```

---

# 49. Cross-Repository Scripts

Scripts touching both repos must receive both roots explicitly or discover each repo independently.

Bad:

```powershell
$LmsNgRoot = $WhizdomRoot.Replace("WhizdomLift", "lms-ng")
```

Good:

```powershell
-LmsNgRoot "C:\NST\Software Dev\lms-ng" `
-WhizdomRoot "C:\NST\Software Dev\WhizdomLift"
```

Production equivalent:

```powershell
-LmsNgRoot "D:\lms-ng" `
-WhizdomRoot "D:\WhizdomLift"
```

---

# 50. Commit/Push End-of-Task Checklist

Before finishing any task with repository changes:

```text
[ ] Correct environment identified
[ ] Correct WhizdomLift repo path
[ ] origin matches Meltingth/WhizdomLift
[ ] Correct branch
[ ] AGENTS.md read
[ ] Capture not disturbed
[ ] No unauthorized COM access
[ ] No unauthorized Scheduled Task modification
[ ] No unauthorized firmware change
[ ] Contract vendored bytes unchanged unless authorized
[ ] Tests executed
[ ] git diff reviewed
[ ] secrets/logs scan completed
[ ] Atomic changes committed
[ ] Commits pushed
[ ] Local HEAD equals upstream HEAD
[ ] Working tree clean or exceptions documented
[ ] Commit SHAs recorded
[ ] Evidence paths recorded
[ ] Gate unchanged unless explicitly approved
```

Final response includes:

```text
environment:
repoPath:
remote:
branch:
commit(s):
pushStatus:
tests:
captureImpact:
contractImpact:
filesChanged:
knownIssues:
gateStatus:
nextAllowedAction:
```

---

# 51. Stop Conditions

STOP and request Architect decision if:

```text
Contract defect
need to open real COM
need to stop/restart Capture
need to alter Scheduled Task
need to flash firmware
need to alter deployed log_lift.py
unknown elevator-side effect
possible data-loss risk
possible secret exposure
unexpected main modification
remote mismatch
repo-path ambiguity
need to rewrite Git history
need to force-push
unclear gate authorization
```

Do not improvise around these boundaries.

---

# 52. Core Principle

The objective is not to make tests look green.

The objective is to preserve elevator telemetry safely while building a system whose behavior is independently provable.

Every meaningful WhizdomLift change must remain traceable:

```text
requirement
→ code
→ offline test
→ evidence
→ commit
→ push
→ independent audit
→ Architect review
→ approved canary/deployment
```

DEV is the primary development environment.

GitHub is the source of committed code.

Dell is the Production/runtime environment.

The running Capture system remains protected until explicitly handed over by an approved gate.