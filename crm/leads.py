"""Lead sending safeguards and status transitions."""

from crm.database import Database


class OptedOutError(Exception):
    """Raised when outreach is attempted for an opted-out business."""


# minimal version, full behavior completed in T6.1/T6.3/T8.1
def check_opt_out_before_send(business_id: int, db: Database) -> None:
    """Raise OptedOutError when the persisted business has opted out."""
    with db._connect() as connection:
        row = connection.execute(
            "SELECT opt_out FROM businesses WHERE id = ?", (business_id,)
        ).fetchone()
    if row is not None and row["opt_out"]:
        raise OptedOutError(f"Business {business_id} has opted out of outreach.")


# minimal version, full behavior completed in T6.1/T6.3/T8.1
STATUS_FLOW = {
    "New": {"Contacted"},
    "Ready": {"Contacted"},
    "Contacted": {"Contacted"},
    "Replied": {"Contacted"},
    "Meeting": set(),
    "Client": set(),
}


# minimal version, full behavior completed in T6.1/T6.3/T8.1
def transition_status(business_id: int, new_status: str, db: Database) -> None:
    """Apply a status transition allowed by the minimal status-flow map."""
    with db._connect() as connection:
        row = connection.execute(
            "SELECT status FROM businesses WHERE id = ?", (business_id,)
        ).fetchone()
    if row is None:
        raise ValueError(f"Business {business_id} was not found.")
    if new_status not in STATUS_FLOW.get(row["status"], set()):
        raise ValueError(
            f"Cannot transition business {business_id} from {row['status']} to {new_status}."
        )
    db.update_status(business_id, new_status)
