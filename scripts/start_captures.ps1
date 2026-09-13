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

    EVERY RUN APPENDS TO capture_launcher.log. That is not decoration. Run
    from a Scheduled Task this script has no console: it returned exit code 0
    for seven and a half hours while starting nothing, and the task reported
    "result=0" the whole time, which is the self-contradicting report of
    CLAUDE.md 6.15 with nowhere to read the contradiction. The log is where
    that evidence now lives.

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File D:\WhizdomLift\scripts\start_captures.ps1

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File D:\WhizdomLift\scripts\start_captures.ps1 -Lifts 1,2,3,5
#>
[CmdletBinding()]
param(
    # A STRING, not [int[]], and that is deliberate. Invoked through
    # "powershell.exe -File script.ps1 -Lifts 1,2,3,5" - which is how a
    # Scheduled Task runs it - the arguments arrive as plain strings and
    # PowerShell binds "1,2,3,5" to [int[]] by parsing it as ONE number,
    # reading the commas as thousands separators: [int]"1,2,3,5" = 1235.
    # The script then hunted for a lift 1235 every 15 minutes for seven and a
    # half hours and exited 0 each time. Taking a string and splitting it here
    # behaves the same from -File, from -Command, and interactively.
    [string] $Lifts = '1,2,3,5',
    [string] $Python = $null
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$LogPath = Join-Path $root 'capture_launcher.log'

function Say([string] $msg) {
    $line = '{0}  {1}' -f (Get-Date).ToString('yyyy-MM-dd HH:mm:ss'), $msg
    Write-Host $msg
    try { Add-Content -Path $LogPath -Value $line -Encoding UTF8 } catch { }
}

# Who is running this, and how? A run from a Scheduled Task and a run from a
# console differ in exactly the ways that broke this before, so both are on
# the record rather than assumed.
Say ('--- run start | user=' + $env:USERNAME +
     ' | interactive=' + [Environment]::UserInteractive +
     ' | session=' + (Get-Process -Id $PID).SessionId +
     ' | cwd=' + (Get-Location).Path + ' ---')

try {
    if (-not $Python) {
        $cmd = Get-Command python -ErrorAction SilentlyContinue
        $Python = if ($cmd) { $cmd.Source } else { 'C:\Python312\python.exe' }
        Say ('python resolved to ' + $Python + $(if ($cmd) { ' (from PATH)' } else { ' (fallback - not on PATH here)' }))
    }
    if (-not (Test-Path $Python)) {
        Say ('FATAL python not found at ' + $Python)
        exit 2
    }

    # pyserial is installed per-user, under
    # %APPDATA%\Python\Python312\site-packages. A process started from a
    # Scheduled Task does not get that directory on sys.path - APPDATA is set,
    # but Python's user-site is disabled in that context - so every logger the
    # task started died on "import serial" at line 25 before writing a single
    # line. The task still reported result=0. Putting the directory on
    # PYTHONPATH here is inherited by everything spawned below.
    # Run a native command and hand back its exit code and output. Two traps
    # in one helper: under ErrorActionPreference 'Stop' anything a native
    # command writes to stderr becomes a TERMINATING error, so a python
    # traceback aborts the script before its own exit-code check can run; and
    # the captured output arrives as an array of lines, which Test-Path and
    # string comparison then quietly fail on.
    function Invoke-Native([string] $exe, [string[]] $arguments) {
        $prev = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        try {
            $out = & $exe @arguments 2>&1 | Out-String
            return @{ Code = $LASTEXITCODE; Out = $out.Trim() }
        } finally {
            $ErrorActionPreference = $prev
        }
    }

    # The question is not "does a site-packages directory exist" - under the
    # task, Test-Path said no for a directory that demonstrably does exist, and
    # putting that directory on PYTHONPATH did not help either: a process
    # started by the Scheduled Task cannot read the user profile at all. So ask
    # the only question that matters - can THIS interpreter, in THIS context,
    # import pyserial - and work down a list of remedies until it can.
    #
    # vendor\ is the one that actually holds, because it lives beside the repo
    # on D: instead of inside a profile:  pip install --target vendor pyserial
    $vendor = Join-Path $root 'vendor'
    $chk = Invoke-Native $Python @('-c', 'import serial')
    if ($chk.Code -ne 0) {
        Say 'pyserial not importable as-is - trying the known locations'
        foreach ($cand in @(
            @{ Name = 'vendor'; Path = $vendor },
            @{ Name = 'user site-packages'
               Path = (Invoke-Native $Python @('-c', 'import site;print(site.getusersitepackages())')).Out }
        )) {
            if (-not $cand.Path) { continue }
            $env:PYTHONPATH = $cand.Path
            $chk = Invoke-Native $Python @('-c', 'import serial')
            Say ('  tried ' + $cand.Name + ' (' + $cand.Path + ') -> ' +
                 $(if ($chk.Code -eq 0) { 'works' } else { 'no' }))
            if ($chk.Code -eq 0) { break }
        }
        if ($chk.Code -ne 0) { $env:PYTHONPATH = $null }
    }
    if ($chk.Code -ne 0) {
        Say 'FATAL this python cannot import pyserial, so every logger would die on startup'
        Say ('  interpreter : ' + $Python)
        Say ('  APPDATA     : ' + $env:APPDATA)
        foreach ($l in ($chk.Out -split "`r?`n" | Where-Object { $_.Trim() })) {
            Say ('  | ' + $l)
        }
        Say '  fix it once - no administrator rights needed, and it puts the'
        Say '  package outside the user profile where a task can reach it:'
        Say ('    & "' + $Python + '" -m pip install --target "' + $vendor + '" pyserial')
        exit 4
    }
    Say ('pyserial import check passed' +
         $(if ($env:PYTHONPATH) { ' via ' + $env:PYTHONPATH } else { ' (already on sys.path)' }))

    function Get-RunningLifts {
        # The second positional argument of log_lift.py is the lift. Matching
        # the first one as COM\d+ would miss a capture started as "auto" and
        # report a running logger as absent - which would then start a second.
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

    $wanted = @($Lifts -split '[,;\s]+' | Where-Object { $_ -ne '' })
    $bad = @($wanted | Where-Object { $_ -notmatch '^[0-9]+$' })
    if ($bad.Count -or $wanted.Count -eq 0) {
        Say ("FATAL cannot read -Lifts '$Lifts' as a list of lift numbers" +
             $(if ($bad.Count) { ' (bad: ' + ($bad -join ',') + ')' } else { '' }))
        exit 2
    }
    Say ('lifts requested: ' + ($wanted -join ', '))

    $running = Get-RunningLifts
    Say ('already capturing: ' + $(if ($running.Count) {
            (($running.Keys | Sort-Object) | ForEach-Object { "$_=$($running[$_].Pid)" }) -join ' '
        } else { '(none)' }))

    # A process started by the Scheduled Task reports an EMPTY CommandLine to
    # a query from an ordinary shell, so Get-RunningLifts cannot see it and
    # would start a second logger on the same lift - the corruption CLAUDE.md
    # 6.8 exists to prevent. Process EXISTENCE is still visible, so the logger
    # leaves its pid in capture_lift_<n>.pid and that is what gets checked.
    #
    # An earlier version used the log file's timestamp instead. That was worse
    # in a way worth remembering: a logger killed ten seconds ago has a log
    # that looks exactly as fresh as a live one, so the guard protected three
    # dead captures and the watchdog left them dead. A pid either exists or it
    # does not.
    function Test-PidAlive([string] $lift) {
        $f = Join-Path $root ("capture_lift_{0}.pid" -f $lift)
        if (-not (Test-Path -LiteralPath $f)) { return $false }
        $id = (Get-Content -LiteralPath $f -Raw).Trim()
        if ($id -notmatch '^\d+$') { return $false }
        $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$id" -ErrorAction SilentlyContinue
        return ($null -ne $proc -and $proc.Name -eq 'python.exe')
    }

    $missing = @()
    foreach ($l in $wanted) {
        if ($running.ContainsKey("$l")) { continue }
        if (Test-PidAlive $l) {
            Say ("lift $l is not visible in the process table but its pid file points at a live python - leaving it alone")
            continue
        }
        $missing += $l
    }
    if ($missing.Count -eq 0) {
        Say 'nothing to start - every requested lift is already capturing'
        exit 0
    }
    Say ('missing, will start: ' + ($missing -join ', '))

    # One shared identity scan. It never transmits, and a port another capture
    # holds comes back as "claimed" and is left alone.
    $map = @{}
    try {
        Say 'resolving ports by identity (a moment per free port)'
        # Keep stdout and stderr apart. Merging them with 2>&1 turns any
        # Python warning into a PowerShell error under ErrorActionPreference
        # 'Stop', and the log then shows one meaningless line of a traceback.
        $scan = Invoke-Native $Python @('port_resolver.py', '--json')
        if ($scan.Code -ne 0) {
            foreach ($l in ($scan.Out -split "`r?`n" | Where-Object { $_.Trim() })) {
                Say ('  port_resolver: ' + $l)
            }
            throw ('port_resolver exited ' + $scan.Code)
        }
        $rows = $scan.Out | ConvertFrom-Json
        foreach ($row in $rows) {
            if ($row.state -eq 'identified') { $map[[string]$row.lift] = $row.port }
        }
        Say ('scan says: ' + $(if ($rows) {
                ($rows | ForEach-Object { "$($_.port)=$(if ($_.state -eq 'identified') { 'lift' + $_.lift } else { $_.state })" }) -join ' '
            } else { '(no rows)' }))
    } catch {
        Say ('port scan failed (' + $_.Exception.Message + ') - every lift will start with auto')
    }

    foreach ($lift in $missing) {
        $port = if ($map.ContainsKey("$lift")) { $map["$lift"] } else { 'auto' }
        # not $args: that is an automatic variable in PowerShell
        $procArgs = @('log_lift.py', $port, "$lift", '--listen', '--follow')
        # Start-Process is enough. An earlier version used Win32_Process.Create
        # to escape the task's job object, on the theory that the task killed
        # its own children - it does not: a logger started this way from the
        # task has since run for hours. What actually killed them was
        # "import serial" failing, which the check above now prevents.
        try {
            $p = Start-Process -FilePath $Python -ArgumentList $procArgs `
                               -WorkingDirectory $root -WindowStyle Hidden -PassThru
            Say ("lift $lift started on $port as pid $($p.Id)")
        } catch {
            Say ("lift $lift FAILED to start on ${port}: " + $_.Exception.Message)
        }
        Start-Sleep -Seconds 2      # let each claim its port before the next looks
    }

    # Did the processes this run started actually survive the run? A Scheduled
    # Task can tear down its own job object on exit and take them with it, and
    # that failure is invisible from inside the run that caused it.
    Start-Sleep -Seconds 8
    $after = Get-RunningLifts
    $alive = @($missing | Where-Object { $after.ContainsKey("$_") -or (Test-PidAlive $_) })
    $dead = @($missing | Where-Object { -not ($after.ContainsKey("$_") -or (Test-PidAlive $_)) })
    Say ('8s later - alive: ' + $(if ($alive) { $alive -join ',' } else { 'none' }) +
         '  gone: ' + $(if ($dead) { $dead -join ',' } else { 'none' }))
    if ($dead.Count) {
        Say 'WARNING processes started by this run are already gone - they are being killed, not failing to start'
    }
    Say '--- run end ---'
} catch {
    Say ('UNHANDLED ' + $_.Exception.GetType().Name + ': ' + $_.Exception.Message)
    Say ('  at ' + $_.InvocationInfo.PositionMessage)
    Say '--- run end (error) ---'
    exit 3
}
