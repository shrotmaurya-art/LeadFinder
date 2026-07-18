"""Pure recommendation engine for leads. No DB access, no side effects."""


def recommend_services(latest_audit: dict) -> list[str]:
    """Return up to 3 prioritised service recommendations, or [] if none needed.

    Priority order (stop at 3 items):
        1. "Website"              — if not has_website
        2. "Business Email Setup" — if not has_business_email
        3. "Google Business / Instagram Optimization" — if review_count < 20 or not has_instagram
    """
    result: list[str] = []

    if not latest_audit.get("has_website"):
        result.append("Website")

    if not latest_audit.get("has_business_email"):
        result.append("Business Email Setup")

    review_count = latest_audit.get("review_count", 0)
    if review_count < 20 or not latest_audit.get("has_instagram"):
        result.append("Google Business / Instagram Optimization")

    return result[:3]
