"""Database backup utility (T10.4)."""

import sqlite3
from pathlib import Path

from crm.database import DEFAULT_DB_PATH
from utils.logger import get_logger
from utils.timeutil import today_local

logger = get_logger(__name__)


def run(db_path: Path | str | None = None) -> Path:
    """Snapshot the SQLite database before any writes happen."""
    source_path = Path(db_path) if db_path else DEFAULT_DB_PATH
    if not source_path.exists():
        logger.info("Database file %s does not exist yet; skipping backup.", source_path)
        return source_path

    backup_dir = source_path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    backup_filename = f"leads_{today_local().replace('-', '')}.db"
    backup_path = backup_dir / backup_filename

    with sqlite3.connect(source_path) as source_conn:
        with sqlite3.connect(backup_path) as dest_conn:
            source_conn.backup(dest_conn)

    logger.info("Successfully backed up database to %s", backup_path)
    return backup_path


if __name__ == "__main__":
    run()
