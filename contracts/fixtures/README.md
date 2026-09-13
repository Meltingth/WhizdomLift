# Contract fixtures

`valid/` — payloads that must pass validation against their schema. `invalid/` — payloads that
must be rejected, each named after the one thing wrong with it, so a test failure reads as "the
schema stopped catching X" rather than an opaque fixture ID.

Every fixture uses placeholder UUIDs and `TEST`-shaped identifiers per
`docs/preflight/DATA_CLASSIFICATION.md` — none of these are real building/gateway/elevator
identities.

## `valid/`

- `state_w02_climbing.json` — an ordinary accepted state record: floor 22→23, UP, RUNNING.
  Exercises the full envelope plus a non-empty `changes[]`.
- `state_w05_uncalibrated_code47.json` — proves the schema accepts `floorRaw: "47"` with no
  upper bound tied to the passenger building's 1–46 range, because W-05 runs a different
  physical profile (`WHZ-SERVICE`) and 47 is its real, confirmed top code (blind test,
  12 Sep 2026 18:31 — see `CLAUDE.md` section 3.4). The Edge payload carries only the raw code;
  Backend-side floor resolution (not this payload, not this schema) is what turns 47 into the
  display label "44" per the owner's decision in `docs/preflight/CONTRACT_BASELINE_DIFF.md`.

## `invalid/`

Each file's name states exactly what makes it invalid, so `tests/contract/test_schemas.py`
can assert *which* constraint fired (C02/C03/C05 need to know it wasn't rejected for the wrong
reason), not just that validation failed.
