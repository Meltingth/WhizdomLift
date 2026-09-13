<#
.SYNOPSIS
  Verifies (or, with -Update, refreshes) this repo's vendored copy of the lms-ng contract
  bundle under contracts/.

.DESCRIPTION
  WhizdomLift (Edge) and lms-ng (Server/Web/Contracts/Infra) are two independent repositories
  with NO forced submodule (ADR-001, and the owner's explicit instruction for this round:
  "ยึด 2 repo ... ไม่มี submodule บังคับ"). The contract crosses that boundary as a plain,
  hash-pinned COPY under contracts/ -- the same pattern this repo already uses for
  vendor/pyserial (CLAUDE.md section 6.19). This script is the one place that copy is written
  or checked; nothing else in this repo edits contracts/** by hand.

  Default action (no switches) and -Check are the same thing: recompute the SHA-256 tree hash
  of the vendored contracts/ directory using the exact algorithm lms-ng/scripts/contracts-hash.ps1
  uses (reimplemented here -- see Get-ContractsTreeHash below -- specifically so this check
  needs no access to the lms-ng repo at all, matching "no forced submodule / no CI cycle
  between the two repos"), and compares it against the pin recorded in contracts/SOURCE.md.
  This catches the failure this script exists to prevent: someone hand-editing a vendored
  schema file in THIS repo without updating the pin, which would silently desynchronize the
  Edge's copy of the contract from what lms-ng actually defines.

  -Update actually refreshes the vendored copy FROM a local lms-ng checkout (-LmsNgPath) --
  this is the only mutating path in this script, and it is never invoked automatically by
  anything (no CI cycle; this round's plan explicitly required "no CI cycle" for this exact
  reason -- the two repos should never be able to silently push contract changes into each
  other without a human running this script on purpose).

.PARAMETER Check
  Explicit spelling of the default (no-switch) behavior: verify only, mutate nothing.

.PARAMETER Update
  Copy contracts/ fresh from -LmsNgPath, overwrite contracts/SOURCE.md with the new pin.
  Requires -LmsNgPath. Fails loudly (does not silently fall back to -Check) if the path does
  not exist or has no contracts/VERSION file.

.PARAMETER LmsNgPath
  Path to a local lms-ng repository checkout. Required with -Update. Never defaulted to a
  guessed path -- an accidental sync from the wrong checkout would silently pin the wrong
  contract bytes.

.EXAMPLE
  D:\WhizdomLift-wt\feature-lms-ng-revise-v2\scripts\sync-contracts.ps1
      # -Check (default): verifies the vendored copy against its own recorded pin. Read-only.
  D:\WhizdomLift-wt\feature-lms-ng-revise-v2\scripts\sync-contracts.ps1 -Update -LmsNgPath D:\lms-ng
      # refreshes the vendored copy from a local lms-ng checkout
#>
[CmdletBinding()]
param(
    [switch]$Check,
    [switch]$Update,
    [string]$LmsNgPath
)

$ErrorActionPreference = 'Stop'

# See lms-ng/scripts/contracts-hash.ps1's own header comment for why this is read in the body
# rather than the param block default: $PSScriptRoot reads empty inside a CmdletBinding()
# param default expression on this host (Windows PowerShell 5.1, invoked via -File).
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
$vendoredContracts = Join-Path $repoRoot 'contracts'
$sourceFile = Join-Path $vendoredContracts 'SOURCE.md'

$excludeNames = @('RELEASE_MANIFEST.json', 'SOURCE.md')
$latin1 = [System.Text.Encoding]::GetEncoding('ISO-8859-1')
$sha256Provider = [System.Security.Cryptography.SHA256]::Create()

function Get-ContractsTreeHash([string]$Path) {
    $root = (Resolve-Path -LiteralPath $Path).Path.TrimEnd('\')
    $files = Get-ChildItem -LiteralPath $root -Recurse -File |
        Where-Object { $excludeNames -notcontains $_.Name }
    if (-not $files -or $files.Count -eq 0) {
        throw "no files found under $root (after exclusions) -- refusing to hash an empty bundle"
    }
    $entries = foreach ($f in $files) {
        $relPath = $f.FullName.Substring($root.Length + 1).Replace('\', '/')
        $bytes = [System.IO.File]::ReadAllBytes($f.FullName)
        $raw = $latin1.GetString($bytes)
        $normalized = $raw -replace "`r`n", "`n" -replace "`r", "`n"
        $normalizedBytes = $latin1.GetBytes($normalized)
        $hashBytes = $sha256Provider.ComputeHash($normalizedBytes)
        $hashHex = ([System.BitConverter]::ToString($hashBytes) -replace '-', '').ToLowerInvariant()
        [PSCustomObject]@{ RelPath = $relPath; Hash = $hashHex }
    }
    # `Sort-Object -CaseSensitive` does NOT produce a true ordinal/byte-value sort on Windows
    # PowerShell 5.1 -- -CaseSensitive only breaks ties on case within an otherwise
    # culture-aware comparison, so e.g. "README.md" sorts AFTER "mqtt/..." despite 'R' (0x52)
    # being a lower byte value than 'm' (0x6D). Caught by tests/test_contracts.py in this same
    # repo, which reimplements this algorithm a third time in Python (plain list.sort() on str
    # IS codepoint-ordinal there) and disagreed with this function's tree hash on real files --
    # not a hypothetical, a reproduced bug. Sorted through .NET's actual ordinal comparer
    # instead, matching lms-ng/scripts/contracts-hash.ps1's identical fix.
    $sortedPaths = New-Object 'System.Collections.Generic.List[string]'
    foreach ($e in $entries) { $sortedPaths.Add($e.RelPath) }
    $sortedPaths.Sort([System.StringComparer]::Ordinal)
    $hashByPath = @{}
    foreach ($e in $entries) { $hashByPath[$e.RelPath] = $e.Hash }
    $manifestLines = foreach ($p in $sortedPaths) { "$($p):$($hashByPath[$p])" }
    $manifestText = ($manifestLines -join "`n") + "`n"
    $treeHashBytes = $sha256Provider.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($manifestText))
    return ([System.BitConverter]::ToString($treeHashBytes) -replace '-', '').ToLowerInvariant()
}

if ($Update) {
    if (-not $LmsNgPath) {
        throw '-Update requires -LmsNgPath <path to a local lms-ng repo checkout>'
    }
    $lmsNgResolved = Resolve-Path -LiteralPath $LmsNgPath
    $sourceContracts = Join-Path $lmsNgResolved 'contracts'
    $sourceVersionFile = Join-Path $sourceContracts 'VERSION'
    if (-not (Test-Path $sourceContracts)) {
        throw "no contracts/ folder found at $sourceContracts"
    }
    if (-not (Test-Path $sourceVersionFile)) {
        throw "no contracts/VERSION found at $sourceVersionFile -- refusing to sync from a tree with no declared version"
    }
    $sourceVersion = (Get-Content -LiteralPath $sourceVersionFile -Raw).Trim()
    $sourceHash = Get-ContractsTreeHash $sourceContracts

    # Provenance guard, checked BEFORE the existing vendored copy is removed so a refused sync
    # leaves it intact. SOURCE.md records lms-ng's HEAD commit as the source; if contracts/ has
    # uncommitted changes, that commit does not contain the bytes being copied and the pin
    # would silently lie about where they came from. This happened once (a draft.3 re-vendor
    # was run before draft.3 was committed in lms-ng) before this guard existed.
    Push-Location $lmsNgResolved
    try {
        $previousEap = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        $dirty = @(git status --porcelain -- contracts 2>$null)
        $statusExit = $LASTEXITCODE
        $ErrorActionPreference = $previousEap
    } finally {
        Pop-Location
    }
    if ($statusExit -ne 0) {
        throw "could not run 'git status' in $lmsNgResolved -- refusing to vendor without being able to verify provenance"
    }
    if ($dirty.Count -gt 0) {
        throw ("refusing to vendor: $lmsNgResolved has uncommitted changes under contracts/, so " +
               "SOURCE.md would pin a commit that does not contain these bytes. Commit them in " +
               "lms-ng first, then re-run -Update.`n" + ($dirty -join "`n"))
    }

    if (Test-Path $vendoredContracts) {
        Remove-Item -LiteralPath $vendoredContracts -Recurse -Force
    }
    Copy-Item -LiteralPath $sourceContracts -Destination $vendoredContracts -Recurse

    # Re-hash the vendored copy independently after the OS-level copy, rather than trusting
    # that Copy-Item preserved bytes exactly -- this is the same "don't trust the tool without
    # checking, check the actual result" discipline this project's CLAUDE.md section 6.16
    # keeps coming back to.
    $vendoredHash = Get-ContractsTreeHash $vendoredContracts
    if ($vendoredHash -ne $sourceHash) {
        throw ("vendored copy hash sha256:$vendoredHash does not match source tree hash " +
               "sha256:$sourceHash after copy -- the copy step altered file bytes (line " +
               "endings? encoding?); investigate before trusting this vendored contract")
    }

    $lmsNgCommit = 'unknown (lms-ng has no commits yet at sync time)'
    Push-Location $lmsNgResolved
    try {
        # Locally relax $ErrorActionPreference for this one native-command call: with it set
        # to 'Stop' (as this script sets globally above), PowerShell 5.1 turns ANY stderr
        # output from a native exe into a terminating NativeCommandError regardless of stream
        # redirection -- `git rev-parse HEAD` exits non-zero with an "unknown revision"
        # message on stderr when a repo has no commits yet (exactly lms-ng's state before its
        # first commit), which is an expected, handled case here, not a script bug.
        $previousEap = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        $commitCheck = git rev-parse HEAD 2>$null
        $ErrorActionPreference = $previousEap
        if ($LASTEXITCODE -eq 0 -and $commitCheck) { $lmsNgCommit = $commitCheck.Trim() }
    } finally {
        Pop-Location
    }

    $syncedAt = [DateTimeOffset]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ')
    # Single-quoted here-string on purpose: PowerShell treats the backtick as an escape
    # character inside a double-quoted here-string, which would silently mangle the triple-
    # backtick Markdown code fences below. A single-quoted here-string never interprets
    # backticks or $variables, so __TOKEN__ placeholders are substituted afterward instead.
    $sourceMdTemplate = @'
# Vendored contract source

**This file is written by `scripts/sync-contracts.ps1 -Update`. Do not hand-edit contracts/**
in this repo -- the source of truth is the lms-ng repository; this directory is a pinned,
hash-verified copy.

| Field | Value |
|---|---|
| Source repo | lms-ng (local checkout at sync time: `__LMSNGPATH__`) |
| Source commit | `__COMMIT__` |
| Contract version | `__VERSION__` |
| Tree hash (sha256, per contracts-hash.ps1's algorithm, excludes RELEASE_MANIFEST.json and this file) | `sha256:__HASH__` |
| Synced at (UTC) | `__SYNCEDAT__` |
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
'@
    # .Replace() (literal string replace), not -replace (regex) -- a local path or commit
    # hash is never meant to be interpreted as a regex pattern or a $1-style backreference.
    $sourceMdContent = $sourceMdTemplate.
        Replace('__LMSNGPATH__', $LmsNgPath).
        Replace('__COMMIT__', $lmsNgCommit).
        Replace('__VERSION__', $sourceVersion).
        Replace('__HASH__', $sourceHash).
        Replace('__SYNCEDAT__', $syncedAt)
    Set-Content -LiteralPath $sourceFile -Value $sourceMdContent -Encoding UTF8

    Write-Host "Updated vendored contracts to version $sourceVersion"
    Write-Host "Tree hash: sha256:$sourceHash"
    Write-Host "Source commit: $lmsNgCommit"
    exit 0
}

# Default / -Check: read-only verification, no dependency on lms-ng being present.
if (-not (Test-Path $sourceFile)) {
    Write-Error "no contracts/SOURCE.md found at $sourceFile -- run '-Update -LmsNgPath <path>' first"
    exit 2
}
$sourceMdText = Get-Content -LiteralPath $sourceFile -Raw
$pinnedHashMatch = [regex]::Match($sourceMdText, 'sha256:([0-9a-f]{64})')
if (-not $pinnedHashMatch.Success) {
    Write-Error "could not find a pinned sha256:<64 hex> hash inside $sourceFile"
    exit 2
}
$pinnedHash = $pinnedHashMatch.Groups[1].Value
$actualHash = Get-ContractsTreeHash $vendoredContracts

if ($actualHash -eq $pinnedHash) {
    Write-Host "OK: vendored contracts match pinned hash sha256:$actualHash"
    exit 0
} else {
    Write-Error ("MISMATCH: vendored contracts hash sha256:$actualHash does not match " +
                 "the pin in SOURCE.md (sha256:$pinnedHash) -- someone edited a vendored " +
                 "contract file directly, or SOURCE.md is stale. Re-run -Update, do not " +
                 "hand-edit the pin.")
    exit 1
}
