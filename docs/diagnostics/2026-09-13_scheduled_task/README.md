# Raw output from diagnosing the silent scheduled task — 13 Sep 2026

Captured while finding out why the capture watchdog returned `result=0` for
7 h 41 min without starting a single logger. The write-up is CLAUDE.md §6.19;
these are the unedited outputs it rests on.

| file | what was run in the spawned (non-interactive) context | showed |
|---|---|---|
| `wmi_out.txt` | `log_lift.py auto 5 --listen --follow` | `ModuleNotFoundError: No module named 'serial'` — every logger died on its first import |
| `wmi_out2.txt` | print `APPDATA` and `sys.path` | the per-user site-packages holding pyserial was not on the path |
| `wmi_out3.txt` | same import with `PYTHONPATH` set to that folder | still failed — the profile folder was unreadable from that context, which is why pyserial ended up vendored under `vendor/` |
| `wmi_out4.txt`, `wmi_out5.txt` | follow-up probes from the same session | kept as captured |
