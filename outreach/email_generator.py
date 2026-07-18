"""Email generation for outreach campaigns.

Combines a style-varied template skeleton with LLM generation to produce
 personalised cold / follow-up emails.  Every public function is a pure
 function — no database access, no side effects beyond the LLM call.
"""

from __future__ import annotations

from outreach.llm import generate as llm_generate, OllamaUnavailableError
from utils.logger import get_logger

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Template skeletons – three structurally distinct opening styles
# ---------------------------------------------------------------------------

_TEMPLATES: list[str] = [
    # 0  Compliment-first
    (
        "You are a friendly outreach copywriter.\n"
        "Write a 3-4 sentence cold email that opens with a genuine compliment "
        "about the business.  Then naturally pivot to the single biggest gap "
        "in their online presence.  Do NOT claim anything about the business "
        "that isn't stated below.  Do NOT mention any service they already "
        "have.  End with a soft call to action (e.g. 'happy to share a quick "
        "idea' — not a hard sell).  Keep it conversational, under 120 words."
    ),
    # 1  Observation-first
    (
        "You are a friendly outreach copywriter.\n"
        "Write a 3-4 sentence cold email that opens with a specific, helpful "
        "observation about the business's current online footprint.  Then "
        "connect that observation to the single biggest gap listed below.  "
        "Do NOT claim anything about the business that isn't stated below.  "
        "Do NOT mention any service they already have.  End with a soft call "
        "to action (e.g. 'worth a quick chat?' — not a hard sell).  Keep it "
        "conversational, under 120 words."
    ),
    # 2  Direct-offer-first
    (
        "You are a friendly outreach copywriter.\n"
        "Write a 3-4 sentence cold email that opens with a direct, helpful "
        "offer related to the single biggest gap below.  Frame it as "
        "something you can help with — no fluff, no false claims.  Do NOT "
        "claim anything about the business that isn't stated below.  Do NOT "
        "mention any service they already have.  End with a soft call to "
        "action (e.g. 'want me to walk you through it?' — not a hard sell).  "
        "Keep it conversational, under 120 words."
    ),
]

_FOLLOW_UP_TEMPLATE: str = (
    "You are a friendly outreach copywriter.\n"
    "Write a 2-sentence follow-up email.  Reference that this is a follow-up "
    "to a previous message without sounding pushy.  Keep the tone warm and "
    "brief.  Under 50 words."
)


def _build_has_summary(audit: dict) -> str:
    """Return a human-readable list of services the business already has."""
    flags = []
    if audit.get("has_website"):
        flags.append("website")
    if audit.get("has_business_email"):
        flags.append("business email")
    if audit.get("has_instagram"):
        flags.append("Instagram")
    return ", ".join(flags) if flags else "none"


def _fallback_subject(name: str) -> str:
    """Deterministic fallback subject truncated to 8 words."""
    raw = f"Quick idea for {name}"
    return " ".join(raw.split()[:8])


def generate_email(
    business: dict,
    latest_audit: dict,
    recommendations: list[str],
    follow_up_number: int = 0,
) -> dict:
    """Return ``{"subject": str, "body": str}`` for a single outreach email.

    Parameters
    ----------
    business : dict
        Must contain at least ``id``, ``name``, ``city``.
    latest_audit : dict
        Audit flags for this business.
    recommendations : list[str]
        Prioritised service recommendations.
    follow_up_number : int
        0 for first contact, >= 1 for follow-ups.
    """
    name = business["name"]
    city = business["city"]
    biggest_gap = recommendations[0] if recommendations else "grow your online presence"
    has_summary = _build_has_summary(latest_audit)

    # --- pick template ----------------------------------------------------
    if follow_up_number >= 1:
        body_sys = _FOLLOW_UP_TEMPLATE
        template_idx = -1  # sentinel – follow-up has no rotation
        log.info(
            "biz=%s using FOLLOW-UP template (follow_up=%d)",
            business["id"],
            follow_up_number,
        )
    else:
        template_idx = business["id"] % len(_TEMPLATES)
        body_sys = _TEMPLATES[template_idx]
        log.info("biz=%s using template index %d", business["id"], template_idx)

    # --- build user prompt ------------------------------------------------
    if follow_up_number >= 1:
        user_prompt = (
            f"Business: {name} in {city}.\n"
            f"This is follow-up #{follow_up_number}.  "
            f"The original email was about: {biggest_gap}."
        )
    else:
        user_prompt = (
            f"Business: {name} in {city}.\n"
            f"Biggest gap: {biggest_gap}.\n"
            f"The business already has: {has_summary}.\n"
            "Write the email body now."
        )

    # --- generate body ----------------------------------------------------
    try:
        body = llm_generate(body_sys, user_prompt, max_tokens=250)
    except OllamaUnavailableError:
        body = (
            f"Hi {name},\n\n"
            f"I noticed you're based in {city} — great to see local businesses "
            f"thriving.  I wanted to share a quick thought on how you could "
            f"improve your {biggest_gap.lower()}.\n\n"
            f"Happy to chat if you're interested.\n\n"
            f"Best regards"
        )

    # --- generate subject (separate LLM call) -----------------------------
    if follow_up_number >= 1:
        subject_sys = (
            "You are an email subject-line writer.\n"
            "Write a single follow-up subject line.  Keep it under 8 words.  "
            "Reference that this is a follow-up without sounding pushy."
        )
        subject_user = (
            f"Follow-up #{follow_up_number} for {name}.  "
            f"Topic: {biggest_gap}."
        )
    else:
        # Mirror the chosen body template style for subject variety
        _SUBJECT_SYSCALLS = [
            "You are an email subject-line writer.\n"
            "Write a single cold-email subject line that leads with a "
            "compliment.  Under 8 words.  No clickbait.",
            "You are an email subject-line writer.\n"
            "Write a single cold-email subject line that leads with a helpful "
            "observation.  Under 8 words.  No clickbait.",
            "You are an email subject-line writer.\n"
            "Write a single cold-email subject line that leads with a direct "
            "offer.  Under 8 words.  No clickbait.",
        ]
        subject_sys = _SUBJECT_SYSCALLS[template_idx]
        subject_user = f"Business: {name} in {city}.  Topic: {biggest_gap}."

    try:
        subject = llm_generate(subject_sys, subject_user, max_tokens=30)
    except OllamaUnavailableError:
        subject = _fallback_subject(name)

    # Ensure subject is under 8 words regardless
    subject = " ".join(subject.split()[:8])

    return {"subject": subject, "body": body}
