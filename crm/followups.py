"""Daily outreach caps and follow-up candidate selection."""

from datetime import date
import contextlib

import config
from crm.database import Database
from crm.leads import transition_status
from utils.logger import get_logger
from utils.timeutil import today_local

logger = get_logger(__name__)


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


def get_followup_candidates(db: Database) -> list[dict]:
    """Select businesses eligible for follow-up and transition them to 'Ready to Contact'.

    A business qualifies when ALL of the following hold:
    - status is exactly 'Contacted'
    - opt_out is 0
    - follow_up_count < config.MAX_FOLLOW_UPS
    - last_contacted_date is not NULL
    - at least config.COOLDOWN_DAYS have elapsed since last_contacted_date

    Qualifying businesses are transitioned to 'Ready to Contact' and returned.
    """
    today = date.fromisoformat(today_local())

    with contextlib.closing(db._connect()) as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM businesses
            WHERE status = 'Contacted'
              AND opt_out = 0
              AND follow_up_count < ?
              AND last_contacted_date IS NOT NULL
            """,
            (config.MAX_FOLLOW_UPS,),
        ).fetchall()

    candidates: list[dict] = []
    for row in rows:
        biz = dict(row)
        last_contacted = date.fromisoformat(biz["last_contacted_date"])
        days_since = (today - last_contacted).days
        if days_since >= config.COOLDOWN_DAYS:
            logger.info(
                "Follow-up candidate: %s (id=%d, follow_ups=%d, days_since_contact=%d)",
                biz["name"],
                biz["id"],
                biz["follow_up_count"],
                days_since,
            )
            transition_status(biz["id"], "Ready to Contact", db)
            candidates.append(biz)

    if not candidates:
        logger.info("No follow-up candidates found.")

    return candidates
