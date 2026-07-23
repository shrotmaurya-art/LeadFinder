"""Lead sending safeguards and status transitions."""

from crm.database import Database


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
        raise OptedOutError(f"Business {business_id} has opted out of outreach.")


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
