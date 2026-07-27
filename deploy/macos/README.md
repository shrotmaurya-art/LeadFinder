# macOS Deployment — Scheduled Daily Run

## Scheduling with `launchd`

Create a plist in `~/Library/LaunchAgents/com.leadfinder.daily.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.leadfinder.daily</string>
    <key>ProgramArguments</key>
    <array>
        <string>/path/to/LeadFinder/.venv/bin/python</string>
        <string>/path/to/LeadFinder/scripts/run_daily.py</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>7</integer>
        <key>Minute</key>
        <integer>30</integer>
    </dict>
    <key>WorkingDirectory</key>
    <string>/path/to/LeadFinder</string>
    <key>StandardOutPath</key>
    <string>/path/to/LeadFinder/logs/stdout.log</string>
    <key>StandardErrorPath</key>
    <string>/path/to/LeadFinder/logs/stderr.log</string>
    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
```

Load it:
```bash
launchctl load ~/Library/LaunchAgents/com.leadfinder.daily.plist
```

## Scheduling lead time

**Important:** With `config.CITIES` and `config.CATEGORIES` now covering
9 cities and 50+ categories, a full run performs **400-500+ searches**
(city × category), each with a 2-5 second throttling delay per TRAI
compliance (T2.1). This can take **60-90 minutes** (or longer on slower
connections).

Schedule the job at least **60-90 minutes before** you want fresh leads
ready. For example, if you want leads available at 09:00, schedule the
plist at **07:30 or earlier**.

## Dual-entry-point handoff

If you rely on the scheduled job, opening the dashboard afterward will
detect today's scout as already done and skip its own trigger. If you
open the dashboard before the scheduled time, the dashboard's background
trigger runs it instead, and the scheduled job will skip when its time
comes.

Both entry points — the scheduled `scripts/run_daily.py` and the
dashboard-triggered `scripts/auto_scout_runner.py` — share the
`get_last_scout_date()` / `set_last_scout_date()` guard in the database,
so whichever runs first each day "wins" and the second one skips instead
of scouting twice.
