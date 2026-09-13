param([Parameter(Mandatory=$true)][string]$Phase)
$ErrorActionPreference = "Stop"
Write-Host "== LMS-NG deploy for phase $Phase =="
if (Test-Path "docker-compose.yml") {
  docker compose up -d --build
  if ($LASTEXITCODE -ne 0) { throw "docker compose failed" }
  if (Test-Path "database/migrations") { dbmate up; if ($LASTEXITCODE -ne 0) { throw "migrations failed" } }
  $ok = $false
  1..30 | ForEach-Object {
    try { $r = Invoke-WebRequest -UseBasicParsing "http://localhost:3000/health" -TimeoutSec 3; if ($r.StatusCode -eq 200) { $script:ok = $true; break } } catch {}
    Start-Sleep -Seconds 2
  }
  if (-not $ok) { throw "api /health not ready" }
  Write-Host "stack up, /health OK"
}
elseif (Test-Path "lms_gateway_agent.py") {
  # Gateway PC: restart the agent service (installed with NSSM) and confirm it publishes within 90 s
  nssm restart lms-gateway-agent
  if ($LASTEXITCODE -ne 0) { throw "service restart failed" }
  python tools/agent_health.py --wait 90
  if ($LASTEXITCODE -ne 0) { throw "agent did not publish within 90 s" }
  Write-Host "agent restarted and publishing"
}
else { throw "unknown repo layout: no docker-compose.yml or lms_gateway_agent.py" }
exit 0
