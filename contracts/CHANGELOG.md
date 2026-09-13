# Contracts changelog

## 2.0.0-draft.2 — 2026-09-13 — DRAFT, not approved

Single change from `2.0.0-draft.1`, made by explicit owner decision during G-A review (not a
new round of independent drafting): **REST base path changed from `/api/v1` to `/api/v2`** in
`contracts/openapi/LMS_NG_OpenAPI.yaml` (all 14 paths + the `info.description` rationale).

Reasoning recorded by the owner: a legacy v1 OpenAPI baseline already exists; this candidate
changes multiple field semantics that are breaking regardless of base path; PRE-0/A-DRAFT's
"no deployed v1 consumer found" search was scoped to the inspected repositories, this
machine's local filesystem, and the supplied revision-pack artifacts only — it never reached
the Dell/server environment or the deliberately-excluded `LMS-NG Live Dashboard.html`, so it
was never strong enough grounds on its own to justify reusing a legacy base path. `/api/v2`
costs nothing today and removes that risk entirely. Full record:
`docs/preflight/CONTRACT_BASELINE_DIFF.md` section 5 (decision D-07).

No MQTT topic, envelope, WebSocket, or database change accompanies this bump — every other
`draft.1` decision (D-01 through D-06, D-08 through D-13) is carried forward unchanged. This
still counts as a new candidate with a newly-computed tree hash, per this repo's own versioning
rule (`contracts/README.md` "Versioning rule": any schema/topic/table change is a **contract
change**, requiring a version bump — the previous hash
(`sha256:c80b2a1889d0ce8ce56f0f5e8c87634fbe43a37be340d42633c8d854ea5ae225`) is retired, not
reused, and must not be cited as this candidate's hash).

## 2.0.0-draft.1 — 2026-09-13 — DRAFT, not approved (superseded by draft.2 above)

First candidate contract for LMS-NG, superseding the v1 baseline found inside the revision
pack (`docs/revisions/.../reference/legacy-contracts/`). Full field-by-field reasoning in
`docs/preflight/CONTRACT_BASELINE_DIFF.md`. Headline changes:

- **Topic root split by data plane**: `lms/v2/...` for REAL, `lms-sim/v2/...` for TEST/SIM,
  rather than relying on ID values alone to separate them.
- **Envelope sequencing redesigned**: `streamId`/`producerId`/`producerEpoch`/`streamSeq`
  (decimal string) replaces the v1 baseline's plain-integer `bootId`+`sequence`, so a Gateway
  restart no longer implicitly resets the meaningful ordering context, and a counter that runs
  for months never silently loses precision in a JavaScript consumer.
- **`floorDisplay` removed from the Edge's MQTT `state` payload.** The v1 baseline had the
  Gateway compute and publish a floor label directly — this contradicted the project's own
  governing documents (Backend Plan v1.3, CLAUDE.md) which make the Backend the single owner
  of floor labels. Corrected, not just versioned.
- **New `origin`/`clockQuality`/`sourceRef` envelope fields** so LIVE/SIMULATED/IMPORT data can
  never be confused with each other and a consumer can refuse to certify latency across an
  unsynced clock pair.
- **Application-level ACK, three-state (`PENDING → TRANSPORT_ACKED → DB_COMMITTED`)** replacing
  the v1 baseline's implicit reliance on MQTT PUBACK as if it were a database guarantee.
- **`status/birth` + `status/will` merged into one retained `status/presence` topic** with a
  monotonic `connectionSeq`, so two retained values can no longer disagree with each other.
- **New topics**: `telemetry/.../snapshot` (retained cache hint, separated from the now
  non-retained durable `state` stream), `events/gateway` (Gateway-lifecycle events, separated
  from elevator-scoped events), `delivery/acks` (server→gateway durability acknowledgement,
  explicitly not a lift command), full WebSocket envelope (no v1 precedent existed).
- **Removed**: the v1 baseline's per-signal-point MQTT topic (redundant with the new
  `state.changes[]` array) and the Edge-reported `tripCount` counter (trip definition is now a
  versioned Backend/Analytics concept, not something the Edge counts).
- **Deferred, not dropped**: command request/result topics and config desired/reported topics —
  reasoned deferral to P5-DRY-RUN scope, recorded in the diff document rather than silently
  omitted.
