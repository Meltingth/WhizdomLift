# Contracts changelog

## 2.0.0-draft.1 — 2026-09-13 — DRAFT, not approved

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
