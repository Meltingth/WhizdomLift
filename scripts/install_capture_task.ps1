<#
.SYNOPSIS
    Register a Scheduled Task that keeps the lift captures running.

.DESCRIPTION
    Registers a task for the CURRENT USER that runs scripts\start_captures.ps1:

      * at logon, so a reboot brings the captures back by itself;
      * every 15 minutes after that, as a watchdog - start_captures.ps1 only
        starts what is missing, so a repeat run on a healthy machine prints
        "nothing to start" and exits.

    Together with --follow that covers the three ways a capture goes away:
    the dongle moved to another socket (--follow finds it), the logger died
    (the 15-minute run restarts it), the PC rebooted (the logon trigger).

    WHY THIS TRIES SEVERAL FORMS. An earlier version asked for a repetition
    lasting [TimeSpan]::MaxValue, which Task Scheduler rejects outright:

        The task XML contains a value which is incorrectly formatted or out
        of range. (14,42):Duration:P99999999DT23H59M59S

    [TimeSpan]::Zero is rejected the same way (Duration:PT0S). Omitting the
    duration is the form that means "repeat indefinitely", but which forms a
    given Windows build accepts is not worth guessing at from a script, so
    this tries them in order, stops at the first that registers, and then
    reports what actually got created rather than what it asked for.

    LIMIT worth knowing: a logon task runs when someone logs in. If the
    machine reboots and nobody logs on, nothing starts until somebody does.
    Running without a logged-on user needs stored credentials or S4U, which
    needs an administrator - ask for that only if the Gateway is meant to run
    headless.

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File D:\WhizdomLift\scripts\install_capture_task.ps1

.NOTES
    -WhatIf is deliberately NOT offered. It would skip Register-ScheduledTask,
    which is the only call that can fail here - a dry run would have reported
    success for a script that cannot work. If you want to see the effect
    without keeping it, install and then run uninstall_capture_task.ps1.
#>
[CmdletBinding()]
param(
    [string] $TaskName = 'WhizdomLift captures',
    [int]    $WatchdogMinutes = 15,
    [int[]]  $Lifts = @(1, 2, 3, 5)
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$launcher = Join-Path $PSScriptRoot 'start_captures.ps1'
if (-not (Test-Path $launcher)) { throw "cannot find $launcher" }

$liftArg = ($Lifts -join ',')
$argLine = ("-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden " +
            "-File `"$launcher`" -Lifts $liftArg")

$action = New-ScheduledTaskAction -Execute 'powershell.exe' `
    -Argument $argLine -WorkingDirectory $root

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit ([TimeSpan]::Zero)

$logon = { New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME }
$soon = (Get-Date).AddMinutes(1)

# Most preferred first. Each must return a trigger, or an array of triggers.
$strategies = @(
    @{
        Name = "logon + repeat every ${WatchdogMinutes}m, no end"
        Build = {
            @((& $logon),
              (New-ScheduledTaskTrigger -Once -At $soon `
                  -RepetitionInterval (New-TimeSpan -Minutes $WatchdogMinutes)))
        }
    },
    @{
        Name = "logon + repeat every ${WatchdogMinutes}m for 365 days"
        Build = {
            @((& $logon),
              (New-ScheduledTaskTrigger -Once -At $soon `
                  -RepetitionInterval (New-TimeSpan -Minutes $WatchdogMinutes) `
                  -RepetitionDuration (New-TimeSpan -Days 365)))
        }
    },
    @{
        # No watchdog, but a reboot still brings the captures back. Strictly
        # worse, and the report below says so rather than hiding it.
        Name = 'logon only (no watchdog)'
        Build = { @(& $logon) }
    }
)

if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Write-Host "a task named '$TaskName' already exists - replacing it"
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

$registered = $null
$failures = @()
foreach ($s in $strategies) {
    try {
        $triggers = & $s.Build
    } catch {
        $failures += ("{0}: building the trigger threw: {1}" -f $s.Name, $_.Exception.Message)
        continue
    }
    try {
        Register-ScheduledTask -TaskName $TaskName `
            -Action $action -Trigger $triggers -Settings $settings `
            -Description ("Keeps log_lift.py capturing for lifts $liftArg. " +
                          "Starts what is missing; does nothing when all are up.") `
            -User $env:USERNAME -ErrorAction Stop | Out-Null
        $registered = $s.Name
        break
    } catch {
        $failures += ("{0}: {1}" -f $s.Name, ($_.Exception.Message -replace "`r?`n", ' '))
    }
}

if (-not $registered) {
    Write-Host ''
    Write-Host 'could not register the task. What each attempt said:'
    foreach ($f in $failures) { Write-Host "  - $f" }
    Write-Host ''
    Write-Host 'If every line says "Access is denied", run this from an'
    Write-Host 'elevated PowerShell (Run as administrator).'
    Write-Host ''
    Write-Host 'The captures themselves are unaffected - start them by hand with:'
    Write-Host "  powershell -NoProfile -ExecutionPolicy Bypass -File `"$launcher`""
    exit 1
}

# Report what was actually created, read back from the registered task, not
# from what this script asked for.
$task = Get-ScheduledTask -TaskName $TaskName
$rep = @($task.Triggers | ForEach-Object { $_.Repetition.Interval } |
         Where-Object { $_ })

Write-Host ''
Write-Host "registered '$TaskName' for $env:USERNAME"
Write-Host ("  strategy used : {0}" -f $registered)
Write-Host ("  triggers      : {0}" -f ($task.Triggers.Count))
Write-Host ("  repetition    : {0}" -f $(if ($rep) { $rep -join ', ' } else { 'none' }))
Write-Host ("  lifts         : {0}" -f $liftArg)
if ($failures.Count) {
    Write-Host ''
    Write-Host '  earlier attempts that this machine rejected:'
    foreach ($f in $failures) { Write-Host "    - $f" }
}
if (-not $rep) {
    Write-Host ''
    Write-Host '  NOTE: no repeating trigger, so there is no 15-minute watchdog.'
    Write-Host '  A reboot still restarts the captures, but a logger that dies'
    Write-Host '  in between will stay dead until the next logon.'
}

Write-Host ''
Write-Host 'run it now without waiting:'
Write-Host "  Start-ScheduledTask -TaskName '$TaskName'"
Write-Host 'then check:'
Write-Host "  cd `"$root`"; python capture_status.py"
Write-Host 'remove it again:'
Write-Host "  powershell -NoProfile -ExecutionPolicy Bypass -File `"$(Join-Path $PSScriptRoot 'uninstall_capture_task.ps1')`""
