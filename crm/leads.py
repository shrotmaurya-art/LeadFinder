"""Lead sending safeguards and status transitions."""

from utils.logger import get_logger
from crm.database import Database

logger = get_logger(__name__)


class OptedOutError(Exception):
    """Raised when outreach is attempted for an opted-out business."""


class InvalidStatusTransitionError(Exception):
    """Raised when a status transition is not allowed by STATUS_FLOW."""


def check_opt_out_before_send(business_id: int, db: Database) -> None:
    """Raise OptedOutError when the persisted business has opted out."""
    with db._connect() as connection:
        row = connection.execute(
            "SELECT opt_out FROM businesses WHERE id = ?", (business_id,)
        ).fetchone()
    if row is not None and row["opt_out"]:
        raise OptedOutError(
            f"Business {business_id} has opted out, refusing to prepare a message"
        )


def mark_opt_out(business_id: int, reason: str, db: Database) -> None:
    """Set opt_out=1 on the business and transition its status to Closed."""
    db.set_opt_out(business_id, True)
    logger.info("Business %d opted out: %s", business_id, reason)
    try:
        transition_status(business_id, "Closed", db)
    except InvalidStatusTransitionError:
        logger.info(
            "Business %d was already Closed; skipping status transition.", business_id
        )


STATUS_FLOW: dict[str, set[str]] = {
    "New": {"Ready to Contact", "Closed"},
    "Ready to Contact": {"Contacted", "Closed"},
    "Contacted": {"Replied", "Ready to Contact", "Closed"},
    "Replied": {"Meeting Scheduled", "Closed"},
    "Meeting Scheduled": {"Client", "Closed"},
    "Client": {"Closed"},
    "Closed": set(),
}


def transition_status(business_id: int, new_status: str, db: Database) -> None:
    """Apply a status transition allowed by STATUS_FLOW.

    Raises InvalidStatusTransitionError when the target status is not a
    valid successor of the business's current status.
    """
    with db._connect() as connection:
        row = connection.execute(
            "SELECT status FROM businesses WHERE id = ?", (business_id,)
        ).fetchone()
    if row is None:
        raise ValueError(f"Business {business_id} was not found.")
    current = row["status"]
    allowed = STATUS_FLOW.get(current, set())
    if new_status not in allowed:
        raise InvalidStatusTransitionError(
            f"Cannot move from {current} to {new_status}"
        )
    db.update_status(business_id, new_status)
