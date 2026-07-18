"""Duplicate detection for candidate business records before insertion."""

from rapidfuzz import fuzz

from crm.database import Database
from scout.normalize import normalize_address
from utils.logger import get_logger


logger = get_logger(__name__)

SOFT_MATCH_THRESHOLD = 90


def is_duplicate(candidate: dict, db: Database) -> tuple[bool, int | None]:
    """Return whether a candidate duplicates an existing business and its ID.

    An exact normalized phone or website match is checked first, avoiding the
    more expensive fuzzy comparisons whenever a certain match is available.
    """
    hard_match = db.find_by_phone_or_website(
        candidate.get("normalized_phone"), candidate.get("normalized_website")
    )
    if hard_match is not None:
        return True, hard_match["id"]

    candidate_address = candidate.get("normalized_address") or normalize_address(
        candidate.get("address")
    ) or ""
    candidate_name = candidate.get("name") or ""
    candidate_text = f"{candidate_name} {candidate_address}"

    for existing in db.get_leads(city=candidate.get("city")):
        existing_address = existing.get("normalized_address") or normalize_address(
            existing.get("address")
        ) or ""
        existing_name = existing.get("name") or ""
        score = fuzz.token_sort_ratio(
            candidate_text, f"{existing_name} {existing_address}"
        )
        is_soft_match = score >= SOFT_MATCH_THRESHOLD
        logger.info(
            "Soft match comparison candidate=%r existing=%r score=%.2f duplicate=%s",
            candidate_name,
            existing_name,
            score,
            is_soft_match,
        )
        if is_soft_match:
            return True, existing["id"]

    return False, None
