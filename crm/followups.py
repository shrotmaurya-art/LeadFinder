"""Daily outreach caps."""

import config
from crm.database import Database
from utils.timeutil import today_local


# minimal version, full behavior completed in T6.1/T6.3/T8.1
def enforce_daily_cap(channel: str, db: Database) -> bool:
    """Return True when today's channel-specific contact cap has been reached."""
    caps = {
        "email": config.EMAIL_DAILY_CAP,
        "whatsapp": config.WHATSAPP_DAILY_CAP,
    }
    if channel not in caps:
        raise ValueError(f"Unsupported outreach channel: {channel}")

    with db._connect() as connection:
        row = connection.execute(
            """
            SELECT COUNT(*) AS sent_count
            FROM contact_log
            WHERE channel = ? AND substr(sent_at, 1, 10) = ?
            """,
            (channel, today_local()),
        ).fetchone()
    return row["sent_count"] >= caps[channel]
