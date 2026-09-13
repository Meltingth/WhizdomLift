# Vendored contract source

**This file is written by `scripts/sync-contracts.ps1 -Update`. Do not hand-edit contracts/**
in this repo -- the source of truth is the lms-ng repository; this directory is a pinned,
hash-verified copy.

| Field | Value |
|---|---|
| Source repo | lms-ng (local checkout at sync time: `D:\lms-ng`) |
| Source commit | `1fbff8e04f4713d848685a2d6502b0cb9ec6ae4d` |
| Contract version | `2.0.0-draft.3` |
| Tree hash (sha256, per contracts-hash.ps1's algorithm, excludes RELEASE_MANIFEST.json and this file) | `sha256:b760b68a99a7490ec1d8f75d11de2f3ae22a943d67b4a06f3656e8e78ed7b249` |
| Synced at (UTC) | `2026-09-13T18:22:44Z` |
| Synced by | `scripts/sync-contracts.ps1 -Update` |

## How this hash is computed

Every file under `contracts/` except `RELEASE_MANIFEST.json` (a manifest cannot hash
itself) and this file (`SOURCE.md`, a per-repo vendoring pointer, not contract content) is
LF-normalised and SHA-256'd; the per-file hashes are combined into one sorted manifest and
SHA-256'd again. Identical algorithm in `lms-ng/scripts/contracts-hash.ps1` and in this
script's own `Get-ContractsTreeHash` function -- reimplemented here rather than shared via
import specifically so this repo can verify its own vendored copy with no dependency on the
lms-ng repository being present (ADR-001: no forced submodule, no CI cycle between the repos).

## Verifying this copy has not drifted

```
scripts\sync-contracts.ps1
# or explicitly:
scripts\sync-contracts.ps1 -Check
```

Compares the pin above against a fresh hash of the files currently on disk. A mismatch means
someone edited a vendored contract file in this repo directly, which must never happen --
fix by re-running `-Update` from the correct lms-ng commit, not by hand-editing the pin.
