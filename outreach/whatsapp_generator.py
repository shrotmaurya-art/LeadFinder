"""WhatsApp message generation for outreach campaigns.

Rotating-template approach (same pattern as email_generator) with a
WhatsApp-toned set of 3 skeletons.  Mandatory opt-out line is always
appended unless the LLM already included one — phrase-based detection,
not a bare-word match.
"""

from __future__ import annotations

import re

from outreach.llm import generate as llm_generate, OllamaUnavailableError
from utils.logger import get_logger

log = get_logger(__name__)

OPT_OUT_LINE = " Reply STOP if you'd rather not hear from me again."
_OPT_OUT_MAX = 400 - len(OPT_OUT_LINE)

_OPT_OUT_RE = re.compile(r"reply\s+stop|text\s+stop|opt[\s-]?out", re.IGNORECASE)

# ---------------------------------------------------------------------------
# WhatsApp templates – 3 structurally distinct casual openings, 2-3 sentences
# ---------------------------------------------------------------------------

_TEMPLATES: list[str] = [
    # 0  Compliment-first, casual
    (
        "You are a friendly WhatsApp outreach copywriter.\n"
        "Write a 2-3 sentence message that opens with a genuine, casual "
        "compliment about the business.  Then pivot to the single biggest "
        "gap.  Do NOT claim anything not stated below.  Do NOT mention any "
        "service the business already has.  Keep it warm and conversational, "
        "under 50 words."
    ),
    # 1  Quick observation, casual
    (
        "You are a friendly WhatsApp outreach copywriter.\n"
        "Write a 2-3 sentence message that opens with a quick, helpful "
        "observation about the business's online presence.  Connect it to "
        "the single biggest gap below.  Do NOT claim anything not stated "
        "below.  Do NOT mention any service the business already has.  Keep "
        "it brief and conversational, under 50 words."
    ),
    # 2  Direct but casual offer
    (
        "You are a friendly WhatsApp outreach copywriter.\n"
        "Write a 2-3 sentence message that opens with a casual, direct "
        "offer related to the biggest gap below.  Frame it as something "
        "you can help with — no fluff, no false claims.  Do NOT claim "
        "anything not stated below.  Do NOT mention any service the business "
        "already has.  Keep it brief and conversational, under 50 words."
    ),
]

_FOLLOW_UP_TEMPLATE: str = (
    "You are a friendly WhatsApp outreach copywriter.\n"
    "Write a 2-sentence follow-up message.  Reference that this is a "
    "follow-up to a previous message without sounding pushy.  Keep the "
    "tone warm and casual.  Under 30 words."
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


def _fallback_message(name: str, biggest_gap: str) -> str:
    """Deterministic fallback when Ollama is unreachable."""
    return (
        f"Hi {name}! "
        f"I noticed you could boost your {biggest_gap.lower()} — "
        f"happy to share a quick idea if you're interested."
    )


def generate_whatsapp(
    business: dict,
    latest_audit: dict,
    recommendations: list[str],
    follow_up_number: int = 0,
) -> str:
    """Return a WhatsApp message string, guaranteed ≤ 400 characters.

    The mandatory opt-out line is appended unless the (possibly truncated)
    LLM output already contains an opt-out phrase.
    """
    name = business["name"]
    biggest_gap = recommendations[0] if recommendations else "grow your online presence"
    has_summary = _build_has_summary(latest_audit)

    # --- pick template ----------------------------------------------------
    if follow_up_number >= 1:
        body_sys = _FOLLOW_UP_TEMPLATE
        template_idx = -1
        log.info(
            "biz=%s using FOLLOW-UP WA template (follow_up=%d)",
            business["id"],
            follow_up_number,
        )
    else:
        template_idx = business["id"] % len(_TEMPLATES)
        body_sys = _TEMPLATES[template_idx]
        log.info("biz=%s using WA template index %d", business["id"], template_idx)

    # --- build user prompt ------------------------------------------------
    if follow_up_number >= 1:
        user_prompt = (
            f"Business: {name}.\n"
            f"This is follow-up #{follow_up_number}.  "
            f"The original message was about: {biggest_gap}."
        )
    else:
        user_prompt = (
            f"Business: {name}.\n"
            f"Biggest gap: {biggest_gap}.\n"
            f"The business already has: {has_summary}.\n"
            "Write the WhatsApp message now."
        )

    # --- generate body ----------------------------------------------------
    try:
        raw = llm_generate(body_sys, user_prompt, max_tokens=120)
    except OllamaUnavailableError:
        raw = _fallback_message(name, biggest_gap)

    # --- truncate first, to guarantee room for OPT_OUT_LINE ---------------
    if len(raw) > _OPT_OUT_MAX:
        raw = raw[:_OPT_OUT_MAX - 3].rstrip() + "..."

    # --- check for existing opt-out phrase (phrase, not bare word) ---------
    if _OPT_OUT_RE.search(raw):
        return raw

    return raw + OPT_OUT_LINE
