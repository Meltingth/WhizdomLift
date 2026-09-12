<#
.SYNOPSIS
    Remove the Scheduled Task that keeps the lift captures running.

.DESCRIPTION
    Removes the task only. Captures already running are left alone - stopping
    them is a separate, deliberate act (create the STOP_CAPTURE file in the
    repo root, which every logger checks).

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts\uninstall_capture_task.ps1
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string] $TaskName = 'WhizdomLift captures'
)

$ErrorActionPreference = 'Stop'

$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if (-not $task) {
    Write-Host "no task named '$TaskName' - nothing to remove"
    exit 0
}

if ($PSCmdlet.ShouldProcess($TaskName, 'unregister scheduled task')) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "removed '$TaskName'"
    Write-Host "captures already running were not touched - to stop those,"
    Write-Host "create the file STOP_CAPTURE in the repo root."
}
