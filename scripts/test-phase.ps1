param([Parameter(Mandatory=$true)][string]$Phase)
$ErrorActionPreference = "Stop"
$runner = "tests/phase-$Phase/run.ps1"
if (Test-Path $runner) { & pwsh -File $runner; exit $LASTEXITCODE }
if (Test-Path "package.json") { pnpm test; exit $LASTEXITCODE }
if (Test-Path "pyproject.toml" -or (Test-Path "requirements.txt")) { pytest -q; exit $LASTEXITCODE }
throw "no test runner found for phase $Phase"
