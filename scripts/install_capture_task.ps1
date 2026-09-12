<#
.SYNOPSIS
    Register a Scheduled Task that keeps the lift captures running.

.DESCRIPTION
    Registers a task for the CURRENT USER (no administrator rights needed)
    that runs scripts\start_captures.ps1:

      * at logon, so a reboot brings the captures back by itself;
      * every 15 minutes after that, as a watchdog - start_captures.ps1 only
        starts what is missing, so a repeat run on a healthy machine prints
        "nothing to start" and exits.

    Together with --follow that covers the three ways a capture goes away:
    the dongle moved to another socket (--follow finds it), the logger died
    (the 15-minute run restarts it), the PC rebooted (the logon trigger).

    LIMIT worth knowing: a logon task runs when someone logs in. If the
    machine reboots and nobody logs on, nothing starts until somebody does.
    Running without a logged-on user needs stored credentials or S4U, which
    needs an administrator - ask for that only if the Gateway is meant to run
    headless.

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts\install_capture_task.ps1

.EXAMPLE
    # see what it would register, change nothing
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts\install_capture_task.ps1 -WhatIf
#>
[CmdletBinding(SupportsShouldProcess = $true)]
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
$action = New-ScheduledTaskAction -Execute 'powershell.exe' `
    -Argument ("-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden " +
               "-File `"$launcher`" -Lifts $liftArg") `
    -WorkingDirectory $root

$atLogon = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME

# A repeating trigger is the watchdog. It starts in a minute rather than now
# so installing the task does not race the captures this session already has.
$watchdog = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Minutes $WatchdogMinutes) `
    -RepetitionDuration ([TimeSpan]::MaxValue)

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit ([TimeSpan]::Zero)

$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "a task named '$TaskName' already exists - replacing it"
    if ($PSCmdlet.ShouldProcess($TaskName, 'unregister existing task')) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    }
}

if ($PSCmdlet.ShouldProcess($TaskName, 'register scheduled task')) {
    Register-ScheduledTask -TaskName $TaskName `
        -Action $action -Trigger @($atLogon, $watchdog) -Settings $settings `
        -Description ("Keeps log_lift.py capturing for lifts $liftArg. " +
                      "Starts what is missing; does nothing when all are up.") `
        -User $env:USERNAME | Out-Null

    Write-Host ""
    Write-Host "registered '$TaskName' for $env:USERNAME"
    Write-Host "  at logon, then every $WatchdogMinutes minutes"
    Write-Host "  lifts: $liftArg"
    Write-Host ""
    Write-Host "run it now without waiting:"
    Write-Host "  Start-ScheduledTask -TaskName '$TaskName'"
    Write-Host "remove it again:"
    Write-Host "  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\uninstall_capture_task.ps1"
}
