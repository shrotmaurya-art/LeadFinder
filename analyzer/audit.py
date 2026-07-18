"""Audit logic that evaluates a single business record and appends an audit row."""

from crm.database import Database
from utils.constants import PERSONAL_EMAIL_DOMAINS


def run_audit(business: dict, db: Database) -> dict:
    """Audit a business, save a history row, and return the four audit flags."""
    has_website = bool(business.get("website"))

    email = business.get("email")
    if not email:
        has_business_email = False
    else:
        domain = email.split("@")[-1].lower()
        has_business_email = domain not in PERSONAL_EMAIL_DOMAINS

    has_instagram = bool(business.get("instagram_url"))
    review_count = business.get("google_reviews_count") or 0

    db.save_audit(
        business["id"],
        has_website,
        has_business_email,
        has_instagram,
        review_count,
    )

    return {
        "has_website": has_website,
        "has_business_email": has_business_email,
        "has_instagram": has_instagram,
        "review_count": review_count,
    }
