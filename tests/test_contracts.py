"""contracts/: this repo's vendored copy of the lms-ng contract bundle (ADR-001, no forced
submodule -- contracts cross the Edge/Platform repo boundary as a plain hash-pinned copy, the
same pattern this repo already uses for vendor/pyserial, CLAUDE.md section 6.19).

This test checks the VENDORING itself, not contract correctness -- schema/fixture validation
against JSON payloads is lms-ng's own tests/contract/test_schemas.py job, not this repo's. What
this file guards against is the specific failure scripts/sync-contracts.ps1 exists to prevent:
someone hand-editing a file under contracts/ in THIS repo without updating the pin, silently
desynchronizing the Edge's copy from what lms-ng actually defines.

The tree-hash algorithm is reimplemented a THIRD time here (after lms-ng/scripts/contracts-hash.ps1
and this repo's own scripts/sync-contracts.ps1) deliberately: an independent Python
implementation agreeing with two independent PowerShell implementations is stronger evidence
the algorithm itself is right, not just that one script was copy-pasted into another.

Run: python tests/test_contracts.py
"""
import hashlib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTRACTS = os.path.join(ROOT, "contracts")

fails = 0


def check(name, ok, detail=""):
    global fails
    fails += 0 if ok else 1
    print("%-4s %-70s %s" % ("ok" if ok else "FAIL", name, detail))


EXCLUDE_NAMES = {"RELEASE_MANIFEST.json", "SOURCE.md"}


def tree_hash(root):
    """Same algorithm as lms-ng/scripts/contracts-hash.ps1 and this repo's own
    scripts/sync-contracts.ps1's Get-ContractsTreeHash: exclude RELEASE_MANIFEST.json and
    SOURCE.md, LF-normalise each file's bytes, sha256 per file, sha256 of the sorted
    'relpath:hash' manifest."""
    entries = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            if name in EXCLUDE_NAMES:
                continue
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            with open(full, "rb") as f:
                raw = f.read()
            # latin-1 is a 1:1 byte<->char mapping for 0-255, so this round-trip never
            # corrupts non-UTF-8 content the way decoding as UTF-8 text first could.
            text = raw.decode("latin-1")
            normalized = text.replace("\r\n", "\n").replace("\r", "\n")
            file_hash = hashlib.sha256(normalized.encode("latin-1")).hexdigest()
            entries.append((rel, file_hash))
    entries.sort(key=lambda e: e[0])  # ordinal sort, matches [CaseSensitive] in PowerShell
    manifest_text = "\n".join(f"{rel}:{h}" for rel, h in entries) + "\n"
    return hashlib.sha256(manifest_text.encode("utf-8")).hexdigest()


# 1. the vendored directory exists at all
check("contracts/ exists in this repo", os.path.isdir(CONTRACTS))
if not os.path.isdir(CONTRACTS):
    print("\n%d failure(s) -- contracts/ missing, skipping remaining checks" % (fails or 1))
    sys.exit(1)

# 2. SOURCE.md exists and carries a pinned sha256:<64 hex>
source_md_path = os.path.join(CONTRACTS, "SOURCE.md")
check("contracts/SOURCE.md exists (written by scripts/sync-contracts.ps1 -Update)",
      os.path.isfile(source_md_path))

pinned_hash = None
pinned_version = None
if os.path.isfile(source_md_path):
    source_md = open(source_md_path, encoding="utf-8").read()
    hash_match = re.search(r"sha256:([0-9a-f]{64})", source_md)
    pinned_hash = hash_match.group(1) if hash_match else None
    check("SOURCE.md contains a pinned sha256:<64 hex> tree hash", pinned_hash is not None)

    version_match = re.search(r"\| Contract version \| `([^`]+)` \|", source_md)
    pinned_version = version_match.group(1) if version_match else None
    check("SOURCE.md records a contract version", pinned_version is not None,
          repr(pinned_version))

# 3. the vendored contracts/VERSION file agrees with what SOURCE.md pinned
version_file_path = os.path.join(CONTRACTS, "VERSION")
if os.path.isfile(version_file_path) and pinned_version:
    actual_version = open(version_file_path, encoding="utf-8").read().strip()
    check("contracts/VERSION matches the version pinned in SOURCE.md",
          actual_version == pinned_version,
          f"VERSION={actual_version!r} SOURCE.md={pinned_version!r}")
else:
    check("contracts/VERSION exists", os.path.isfile(version_file_path))

# 4. the actual, independently-recomputed tree hash matches the pin -- this is the check that
#    catches a hand-edited vendored file (the whole reason this test file exists)
if pinned_hash:
    actual_hash = tree_hash(CONTRACTS)
    check("vendored contracts/ tree hash matches the pin in SOURCE.md (no drift)",
          actual_hash == pinned_hash,
          f"actual=sha256:{actual_hash} pinned=sha256:{pinned_hash}")

# 5. the vendored bundle stays unapproved from this side too -- a consumer repo that somehow
#    saw APPROVED/non-null fields when lms-ng's own copy is still DRAFT would itself be a
#    serious desync, independent of the "never self-approve" rule that governs lms-ng directly
#    (that rule is lms-ng's own C06 test's job; this just checks the copy didn't drift on it).
manifest_path = os.path.join(CONTRACTS, "RELEASE_MANIFEST.json")
if os.path.isfile(manifest_path):
    manifest = json.load(open(manifest_path, encoding="utf-8"))
    check("vendored RELEASE_MANIFEST.json status is DRAFT",
          manifest.get("status") == "DRAFT", repr(manifest.get("status")))
    check("vendored RELEASE_MANIFEST.json approvedBy/approvedAt are still null",
          manifest.get("approvedBy") is None and manifest.get("approvedAt") is None,
          f"approvedBy={manifest.get('approvedBy')!r} approvedAt={manifest.get('approvedAt')!r}")
else:
    check("contracts/RELEASE_MANIFEST.json exists", False)

# 6. every version-bearing field in the vendored bundle agrees with contracts/VERSION.
#    Added for candidate 2.0.0-draft.3: an independent audit found a frozen candidate whose
#    enums/ui-enums.yaml named an older candidate than VERSION/RELEASE_MANIFEST did, and no
#    check on either side of the repo boundary noticed. lms-ng's own
#    tests/contract/version_consistency.py is the full check; this is the Edge side's stdlib-only
#    subset (the system Python the Edge runs under has no PyYAML), so a copy that drifted here --
#    or was vendored from an inconsistent source -- fails here too, without importing from lms-ng.
if os.path.isfile(version_file_path):
    version = open(version_file_path, encoding="utf-8").read().strip()

    def first_match(relpath, pattern):
        full = os.path.join(CONTRACTS, relpath)
        if not os.path.isfile(full):
            return None
        m = re.search(pattern, open(full, encoding="utf-8").read(), re.MULTILINE)
        return m.group(1).strip().strip("'\"") if m else None

    if os.path.isfile(manifest_path):
        check("vendored RELEASE_MANIFEST.json version == VERSION",
              manifest.get("version") == version, f"{manifest.get('version')!r} vs {version!r}")
    enums_version = first_match(os.path.join("enums", "ui-enums.yaml"), r"^version:\s*(\S+)")
    check("vendored enums/ui-enums.yaml version == VERSION",
          enums_version == version, f"{enums_version!r} vs {version!r}")
    openapi_version = first_match(os.path.join("openapi", "LMS_NG_OpenAPI.yaml"),
                                  r"^info:\s*$(?:\n[ \t]+.*$)*?\n[ \t]+version:\s*(\S+)")
    check("vendored OpenAPI info.version == VERSION",
          openapi_version == version, f"{openapi_version!r} vs {version!r}")
    changelog_heading = first_match("CHANGELOG.md", r"^## (\S+)")
    check("vendored CHANGELOG.md newest entry == VERSION",
          changelog_heading == version, f"{changelog_heading!r} vs {version!r}")

    stray = []
    for dirpath, _dirnames, filenames in os.walk(CONTRACTS):
        for name in filenames:
            if name in ("CHANGELOG.md", "SOURCE.md"):
                continue
            full = os.path.join(dirpath, name)
            text = open(full, encoding="utf-8", errors="replace").read()
            if name == "RELEASE_MANIFEST.json":
                scrubbed = json.loads(text)
                scrubbed.pop("supersededCandidates", None)
                text = json.dumps(scrubbed)
            for label in re.findall(r"\b\d+\.\d+\.\d+-draft\.\d+\b", text):
                if label != version:
                    stray.append("%s: %s" % (os.path.relpath(full, CONTRACTS), label))
    check("no stray older candidate label anywhere in the vendored bundle",
          not stray, "; ".join(stray[:5]) or "none")

print("\n%d failure(s)" % fails)
sys.exit(1 if fails else 0)
