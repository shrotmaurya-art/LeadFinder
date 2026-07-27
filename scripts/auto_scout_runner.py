"""Auto-scout runner: kicks off today's pipeline in a background thread if not already done."""

import threading

from crm.database import Database
from scripts.run_daily import run_pipeline
from utils.logger import get_logger
from utils.timeutil import today_local

logger = get_logger(__name__)


def run_in_background(db: Database) -> None:
    """Check whether today's scout has run; if not, spawn a daemon thread to do it.

    This function returns immediately so the caller (dashboard) is never blocked.
    """
    today = today_local()
    last = db.get_last_scout_date()

    if last == today:
        logger.info("Scout already ran today, skipping")
        return

    def _background_work() -> None:
        try:
            logger.info("Background scout starting for %s", today)
            run_pipeline(db)
            db.set_last_scout_date(today)
            logger.info("Background scout completed successfully for %s", today)
        except Exception:
            logger.exception("Background scout failed")

    thread = threading.Thread(target=_background_work, daemon=True)
    thread.start()
