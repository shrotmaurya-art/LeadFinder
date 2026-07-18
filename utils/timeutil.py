from datetime import datetime
from zoneinfo import ZoneInfo
import config

def today_local() -> str:
    """Returns today's date as "YYYY-MM-DD" in config.APP_TIMEZONE."""
    tz = ZoneInfo(config.APP_TIMEZONE)
    return datetime.now(tz).date().isoformat()

def now_local_iso() -> str:
    """Returns a full ISO 8601 timestamp in config.APP_TIMEZONE."""
    tz = ZoneInfo(config.APP_TIMEZONE)
    return datetime.now(tz).isoformat()
