# LMS-NG contracts — candidate 2.0.0-draft.1

**Status: DRAFT. Nothing here is approved.** `approvedBy`/`approvedAt` in
`RELEASE_MANIFEST.json` are `null` and stay `null` until the owner says otherwise in chat, in
person, or in writing — not by this repository setting them itself (see
`docs/decisions/G-A_DECISION_PACKET.md` and the guard rule below).

## What's here

- `mqtt/LMS_NG_MQTT_Topic_Specification_v2.yaml` — topic tree, envelope, ACL, example payloads
  in `mqtt/examples/`.
- `json-schema/` — the same contract as executable Draft 2020-12 JSON Schema: `common/` (shared
  enums/ids/time definitions), `mqtt/` (one schema per MQTT message type), `ws/` (WebSocket
  envelope + per-type message shapes).
- `openapi/LMS_NG_OpenAPI.yaml` — REST + WS surface.
- `enums/ui-enums.yaml` — the Thai/English display strings the owner has already fixed
  (`รอติดตั้ง`, `ศูนย์สัญญาณเตือน`, etc.) plus the new enum values this revision adds.
- `fixtures/{valid,invalid}/` — example payloads used by `tests/contract/`.

## Where this came from, and what it changed

Every non-trivial difference from the v1 baseline contracts (shipped as read-only references at
`docs/revisions/LMS_NG_Revised_Execution_Pack_v2_0/reference/legacy-contracts/` on the
WhizdomLift feature branch) is catalogued, row by row, with a reason and a test ID, in
`docs/preflight/CONTRACT_BASELINE_DIFF.md`. Read that before reading the schemas — it explains
*why* a field looks the way it does, which the schema's own `description` strings only summarize.

## Versioning rule

`contracts/VERSION` is the single source of truth for the current candidate version. A
**MINOR** bump (e.g. `2.1.0`) adds something (an optional field, a new enum value, a new
endpoint) without breaking an existing consumer. A **MAJOR** bump (e.g. `3.0.0`) removes or
renames anything, or changes a field's meaning — and runs on a parallel topic root
(`lms/v3/...`) rather than replacing `v2` in place, exactly as this candidate itself did to `v1`.
**Patch** (`2.0.1`) is wording/example changes only, no schema/topic/table change.

## Change guard

`contracts/**` and any `database/migrations/*.sql` file are not edited casually. A change here
is a **contract change**, and per the workflow guard ("no contract changes without a human
decision" — carried into this revision as section 2.1's Gate rules), it requires:

1. A `contracts/VERSION` bump appropriate to the change (above).
2. An entry in `CHANGELOG.md` explaining what changed and why.
3. For anything already past Gate G-A: explicit new owner approval recorded the same way the
   original approval was recorded — never inferred, never defaulted to yes.

Nothing in this repository is set up to bypass that by environment variable, CI flag, or
default value.
