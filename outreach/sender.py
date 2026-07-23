from urllib.parse import quote

from crm import followups, leads
from crm.database import Database


db = Database()
COPY_FALLBACK_LIMIT = 1800


def to_whatsapp_link_format(normalized_phone: str) -> str:
    """Convert a normalized phone number to the digits required by wa.me."""
    return "".join(character for character in normalized_phone.lstrip("+") if character.isdigit())


def prepare_send(business: dict, channel: str, subject: str | None, message: str) -> dict:
    """Build a manual-send link after opt-out and daily-cap safeguards."""
    leads.check_opt_out_before_send(business["id"], db)

    if followups.enforce_daily_cap(channel, db):
        return {"blocked": True, "reason": f"Daily {channel} limit reached"}

    if channel == "email":
        email = business.get("email")
        if not email:
            return {"blocked": True, "reason": "No business email on file"}
        link = f"mailto:{email}?subject={quote(subject or '')}&body={quote(message)}"
    elif channel == "whatsapp":
        phone = business.get("normalized_phone")
        if not phone:
            return {"blocked": True, "reason": "No phone number on file"}
        link = f"https://wa.me/{to_whatsapp_link_format(phone)}?text={quote(message)}"
    else:
        raise ValueError(f"Unsupported outreach channel: {channel}")

    if len(link) > COPY_FALLBACK_LIMIT:
        return {"blocked": False, "link": None, "fallback": "copy"}
    return {"blocked": False, "link": link, "fallback": None}


def confirm_sent(
    business_id: int,
    channel: str,
    message: str,
    follow_up_number: int,
    sent_by: str | None = None,
) -> int:
    """Record a confirmed manual send and update its business state."""
    contact_id = db.log_contact(
        business_id, channel, message, follow_up_number, sent_by
    )
    leads.transition_status(business_id, "Contacted", db)
    db.increment_follow_up(business_id)
    return contact_id
