<#
.SYNOPSIS
    Start a log_lift.py capture for every lift that does not already have one.

.DESCRIPTION
    Idempotent on purpose: it looks at the process table first and only starts
    what is missing, so it is safe to run on a timer as a watchdog. Two
    processes recording one lift is the failure CLAUDE.md 6.8 is about - the
    second would find its port held, search forever and record nothing while
    looking alive.

    Ports are resolved ONCE, up front, by asking each board which lift it is
    (port_resolver.py). Letting four loggers each run their own search at boot
    works but has them queueing behind each other's probes; one shared scan is
    the same answer, sooner. A lift the scan cannot find is started with
    "auto" anyway, so it keeps looking on its own.

    Every capture is started with --follow, so a dongle moved to a different
    USB socket - and therefore a different COM number - is followed by the
    identity its board announces rather than lost.

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts\start_captures.ps1

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts\start_captures.ps1 -Lifts 1,2,3,5
#>
[CmdletBinding()]
param(
    [int[]] $Lifts = @(1, 2, 3, 5),
    [string] $Python = $null
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not $Python) {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    $Python = if ($cmd) { $cmd.Source } else { 'C:\Python312\python.exe' }
}
if (-not (Test-Path $Python)) {
    throw "python not found at '$Python' - pass -Python <path to python.exe>"
}

function Get-RunningLifts {
    # The second positional argument of log_lift.py is the lift. Matching the
    # first one as COM\d+ would miss a capture started as "auto", and report a
    # running logger as absent - which would then start a second one.
    $out = @{}
    Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -like '*log_lift*' } |
        ForEach-Object {
            if ($_.CommandLine -match 'log_lift\.py\s+(\S+)\s+(\S+)') {
                $out[$Matches[2].ToUpper()] = @{ Pid = $_.ProcessId; Port = $Matches[1] }
            }
        }
    return $out
}

$running = Get-RunningLifts
$missing = @($Lifts | Where-Object { -not $running.ContainsKey("$_") })

foreach ($lift in $Lifts) {
    if ($running.ContainsKey("$lift")) {
        $r = $running["$lift"]
        Write-Host ("  lift {0}  already capturing (pid {1}, {2})" -f $lift, $r.Pid, $r.Port)
    }
}

if ($missing.Count -eq 0) {
    Write-Host "nothing to start - every requested lift is already capturing"
    exit 0
}

Write-Host ("starting: {0}" -f ($missing -join ', '))

# One shared identity scan. It never transmits, and a port another capture
# holds comes back as "claimed" and is left alone.
$map = @{}
try {
    Write-Host "  resolving ports by identity (this takes a moment per free port)"
    $json = & $Python 'port_resolver.py' '--json' 2>$null
    foreach ($row in ($json | ConvertFrom-Json)) {
        if ($row.state -eq 'identified') { $map[[string]$row.lift] = $row.port }
    }
} catch {
    Write-Warning "port scan failed ($($_.Exception.Message)) - every lift will start with 'auto'"
}

foreach ($lift in $missing) {
    $port = if ($map.ContainsKey("$lift")) { $map["$lift"] } else { 'auto' }
    # not $args: that is an automatic variable in PowerShell
    $procArgs = @('log_lift.py', $port, "$lift", '--listen', '--follow')
    Start-Process -FilePath $Python -ArgumentList $procArgs `
                  -WorkingDirectory $root -WindowStyle Hidden | Out-Null
    Write-Host ("  lift {0}  started on {1}" -f $lift, $port)
    Start-Sleep -Seconds 2      # let each one claim its port before the next looks
}

Write-Host ""
Write-Host "check with:  $Python capture_status.py"
