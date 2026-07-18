"""Pure scoring function for leads. No DB access, no side effects."""


def score_lead(latest_audit: dict, business: dict) -> int:
    """Return a 0–100 score built from a single audit dict.

    Rubric (independent conditions, sum then cap at 100):
        +25  if not has_website
        +20  if not has_business_email
        +15  if not has_instagram
        +15  if 1 <= review_count <= 20
        +10  if review_count == 0
        +15  if google_rating is not None and >= 4.0
    """
    score = 0

    if not latest_audit.get("has_website"):
        score += 25
    if not latest_audit.get("has_business_email"):
        score += 20
    if not latest_audit.get("has_instagram"):
        score += 15

    review_count = latest_audit.get("review_count", 0)
    if review_count == 0:
        score += 10
    elif 1 <= review_count <= 20:
        score += 15

    google_rating = business.get("google_rating")
    if google_rating is not None and google_rating >= 4.0:
        score += 15

    return min(score, 100)
