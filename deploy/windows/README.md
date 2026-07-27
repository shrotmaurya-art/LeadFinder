# Windows Deployment — Scheduled Daily Run

## Scheduling with Task Scheduler

1. Open **Task Scheduler** and click **Create Task**.
2. **General** tab:  
   - Name: `LeadFinder Daily`  
   - Run whether user is logged on or not  
   - Check **Run with highest privileges** if needed
3. **Triggers** tab:  
   - New → Daily, start at a time you choose (see lead time below)
4. **Actions** tab:  
   - New → Start a program  
   - Program/script: `C:\path\to\LeadFinder\.venv\Scripts\python.exe`  
   - Arguments: `scripts/run_daily.py`  
   - Start in: `C:\path\to\LeadFinder`
5. **Conditions** tab:  
   - Uncheck **Stop if the computer switches to battery power**  
   - Uncheck **Start only if on AC power** (or keep if desired)
6. **Settings** tab:  
   - Check **Run task as soon as possible after a scheduled start is missed**  
   - If the task fails, configure restart as needed

## Scheduling lead time

**Important:** With `config.CITIES` and `config.CATEGORIES` now covering
9 cities and 50+ categories, a full run performs **400-500+ searches**
(city × category), each with a 2-5 second throttling delay per TRAI
compliance (T2.1). This can take **60-90 minutes** (or longer on slower
connections).

Schedule the task at least **60-90 minutes before** you want fresh leads
ready. For example, if you want leads available by 09:00, set the trigger
to **07:30 or earlier**.

## Dual-entry-point handoff

If you rely on the scheduled task, opening the dashboard afterward will
detect today's scout as already done and skip its own trigger. If you
open the dashboard before the scheduled time, the dashboard's background
trigger runs it instead, and the scheduled task will skip when its time
comes.

Both entry points — the scheduled `scripts/run_daily.py` and the
dashboard-triggered `scripts/auto_scout_runner.py` — share the
`get_last_scout_date()` / `set_last_scout_date()` guard in the database,
so whichever runs first each day "wins" and the second one skips instead
of scouting twice.
