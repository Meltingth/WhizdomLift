"""Are the captures still running, and is each one healthy?

Answers the one question you have when you are away from the cabinet:
*is the data still being collected right now?* -- without touching a single
serial port. The loggers hold their ports exclusively (CLAUDE.md 6.12), so
this tool reads only the process table and the log files they write.

    python capture_status.py              # lifts 1, 2, 3, 5
    python capture_status.py 1 3          # just those two
    python capture_status.py --quiet      # one line per lift

exit 0 = every expected lift is capturing and clean
exit 1 = something needs a human

Why it prints the awkward numbers next to the reassuring ones: every bug in
this project announced itself as a self-contradicting report (CLAUDE.md 6.15).
A logger that is "running" while its log has not grown for an hour is exactly
that shape, so both facts share a line.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lift_decode import lift_id           # A-E and 1-5 name the same lifts

DEFAULT_LIFTS = [1, 2, 3, 5]

# A live logger writes the board's identity beacon every 30 s even when the
# car never moves, so silence longer than this is the logger's silence, not
# the lift's (CLAUDE.md 6.3 -- an empty log is not evidence either way).
STALE_SECS = 90

DATA = re.compile(r"^(\d\d:\d\d:\d\d)\.\d\d\d\s+(\d+)\s+([0-9A-Fa-f]{13})")
HEAD = re.compile(r"^===== capture started (\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)"
                  r"\s+lift=(\S+)\s+port=(\S+)")
MARK = re.compile(r"^--- (.*) ---$")
BEACON = re.compile(r"FW IODebug (\S+) (\S+) LIFT=(\d+)")
# The first argument is usually a COM number but may be the literal "auto"
# (--follow resolves it by identity), and the lift may be given as a letter.
# Matching only COM\d+ here made a demonstrably running capture report as
# STOPPED - the report contradicting the log it was reading from.
PROC = re.compile(r"log_lift\.py\s+(\S+)\s+(\S+)", re.I)


def running():
    """lift id -> {pid, port} for every live log_lift.py, asked of the OS."""
    ps = ("Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
          "Where-Object { $_.CommandLine -like '*log_lift*' } | "
          "ForEach-Object { \"$($_.ProcessId)`t$($_.CommandLine)\" }")
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                             capture_output=True, text=True, timeout=60).stdout
    except (OSError, subprocess.SubprocessError) as e:
        print(f"  cannot read the process table ({e}) -- every lift will read "
              f"as STOPPED below, which may be wrong", file=sys.stderr)
        return {}
    found = {}
    for line in out.splitlines():
        pid, _, cmd = line.partition("\t")
        m = PROC.search(cmd)
        if m and pid.strip().isdigit():
            port = m.group(1).upper()
            found[lift_id(m.group(2))] = {
                "pid": int(pid),
                # None means "started with auto" - the command line does not
                # say which port it landed on; the log does.
                "port": port if re.fullmatch(r"COM\d+", port) else None}
    return found


def read_session(path):
    """Facts about the newest capture session in this log file."""
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8", errors="replace") as fh:
        lines = fh.read().splitlines()
    starts = [i for i, l in enumerate(lines)
              if l.startswith("===== capture started")]
    if not starts:
        return None
    i = starts[-1]
    head = HEAD.match(lines[i])
    s = {"start": head.group(1) if head else lines[i][22:41],
         "lift": head.group(2) if head else "?",
         "port": head.group(3).upper() if head else "?",
         "rows": 0, "last_clock": None, "last_ms": None,
         "restarts": [], "link_lost": [], "stopped": False,
         "fw": None, "beacon_lifts": set(),
         # --follow can legitimately move a capture to another COM number.
         # Without reading these back, this tool would call a logger that
         # correctly followed its board DEGRADED for being on the "wrong" port.
         "rebinds": [], "wrong_board": [], "last_search": None,
         "last_marker": None}
    for l in lines[i + 1:]:
        d = DATA.match(l)
        if d:
            s["rows"] += 1
            s["last_clock"], s["last_ms"] = d.group(1), int(d.group(2))
            s["last_marker"] = "data"
            continue
        if l.startswith("===== capture stopped"):
            s["stopped"] = True
            continue
        m = MARK.match(l)
        if not m:
            continue
        body = m.group(1)
        # Every marker the logger writes ends in a wall-clock stamp. All of
        # them count as signs of life -- a capture that is out searching for
        # its board writes no data lines for minutes, and reading only data
        # lines would call that frozen.
        tail = body.split()[-1] if body.split() else ""
        if re.fullmatch(r"\d\d:\d\d:\d\d", tail):
            s["last_clock"] = tail
        b = BEACON.search(body)
        if b:
            s["fw"] = b.group(1) + " " + b.group(2)
            s["beacon_lifts"].add(int(b.group(3)))
            s["last_marker"] = "beacon"
        elif body.startswith("board restarted"):
            s["restarts"].append(body)
            s["last_marker"] = "restart"
        elif body.startswith("link lost"):
            s["link_lost"].append(body)
            s["last_marker"] = "link lost"
        elif body.startswith("rebound to "):
            s["rebinds"].append(body)
            s["last_marker"] = "rebound"
            moved = re.match(r"rebound to (COM\d+)", body)
            if moved:
                s["port"] = moved.group(1)   # where it is now, not where it began
        elif body.startswith("wrong board on "):
            s["wrong_board"].append(body)
            s["last_marker"] = "wrong board"
        elif body.startswith("searching for Lift"):
            s["last_search"] = body
            s["last_marker"] = "search"
    return s


def secs_ago(clock):
    """Seconds between a HH:MM:SS stamp and now.

    The logs carry no date (CLAUDE.md 6.18), so this wraps at midnight: a gap
    over 12 h is read as a clock that just crossed midnight rather than as a
    20-hour-old line. So freshness cannot tell "a minute ago" from "exactly a
    day ago" -- it is a liveness hint. The process table is the fact that
    actually says whether a logger exists.
    """
    if not clock:
        return None
    try:
        h, m, sec = (int(x) for x in clock.split(":"))
    except ValueError:
        return None
    now = datetime.now()
    delta = ((now.hour * 3600 + now.minute * 60 + now.second)
             - (h * 3600 + m * 60 + sec))
    if delta < -43200:
        delta += 86400
    elif delta > 43200:
        delta -= 86400
    return float(delta)


def check(lift, procs):
    path = "capture_lift_%d.log" % lift
    proc = procs.get(lift_id(str(lift)))
    s = read_session(path)
    if s is None:
        return "NO LOG", ["%s has no capture session in it" % path]

    bad = False
    age = secs_ago(s["last_clock"])
    age_txt = "never" if age is None else "%.0fs ago" % age
    span = ""
    try:
        started = datetime.strptime(s["start"], "%Y-%m-%d %H:%M:%S")
        span = " (%.1f d)" % ((datetime.now() - started).total_seconds() / 86400)
    except ValueError:
        pass

    notes = [
        "session %s%s   port %s   rows %s   last line %s (%s)"
        % (s["start"], span, s["port"], format(s["rows"], ","),
           s["last_clock"] or "-", age_txt),
        "firmware %s   board clock %.1f h   restarts %d   link lost %d"
        % (s["fw"] or "no beacon seen", (s["last_ms"] or 0) / 3600000.0,
           len(s["restarts"]), len(s["link_lost"])),
    ]

    wrong = s["beacon_lifts"] - {lift}
    if wrong:
        notes.append("!! the board on this port announced LIFT=%s -- this log "
                     "may hold another lift's data" % sorted(wrong))
        bad = True
    if not s["beacon_lifts"]:
        notes.append("!! no LIFT= beacon in this session -- identity unverified")
        bad = True
    if s["restarts"]:
        notes.append("last restart: " + s["restarts"][-1])
    if s["link_lost"]:
        notes.append("last link loss: " + s["link_lost"][-1])
    if s["rebinds"]:
        notes.append("followed its board %d time(s), last: %s"
                     % (len(s["rebinds"]), s["rebinds"][-1]))
    if s["wrong_board"]:
        notes.append("saw a foreign board: " + s["wrong_board"][-1])

    if proc is None:
        return "STOPPED", notes + ["no log_lift.py process is running for this lift"]
    notes.insert(0, "pid %d  %s" % (proc["pid"], proc["port"] or "auto"))
    if proc["port"] is not None and proc["port"] != s["port"]:
        notes.append("!! process is on %s but the session header says %s -- the "
                     "log was reopened elsewhere" % (proc["port"], s["port"]))
        bad = True
    if s["stopped"]:
        notes.append("!! the newest session in the log is marked stopped, yet a "
                     "process is running -- it is writing somewhere else")
        bad = True
    if age is not None and age > STALE_SECS:
        if s["last_marker"] == "search":
            # --follow holds each port for ~35s while it listens for an
            # identity, so a capture mid-search is working, not wedged.
            return "SEARCHING", notes + ["looking for its board by identity: "
                                         + (s["last_search"] or "")]
        return "STALE", notes + ["process alive but nothing written for %.0fs "
                                 "(a live board beacons every 30s)" % age]
    return ("DEGRADED" if bad else "CAPTURING"), notes


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    quiet = "--quiet" in sys.argv or "-q" in sys.argv
    lifts = [int(a) for a in args] if args else DEFAULT_LIFTS

    if os.path.exists("STOP_CAPTURE"):
        print("STOP_CAPTURE exists -- every logger will exit at its next read\n")

    procs = running()
    worst = 0
    for lift in lifts:
        verdict, notes = check(lift, procs)
        ok = verdict == "CAPTURING"
        worst = max(worst, 0 if ok else 1)
        print("%slift %d  %s" % ("ok " if ok else "!! ", lift, verdict))
        if not quiet:
            for n in notes:
                print("      " + n)
            print()

    extra = sorted(set(procs) - {str(l) for l in lifts})
    if extra:
        print("note: also running, not asked about: "
              + ", ".join("lift %s on %s" % (e, procs[e]["port"]) for e in extra))

    print("ALL CAPTURING" if worst == 0 else "NEEDS ATTENTION")
    return worst


if __name__ == "__main__":
    sys.exit(main())
