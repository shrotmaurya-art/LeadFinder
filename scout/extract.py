import re
from collections import OrderedDict

import requests
from bs4 import BeautifulSoup

from utils.constants import PERSONAL_EMAIL_DOMAINS
from utils.logger import get_logger


logger = get_logger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    )
}
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")


def _fetch(url: str) -> str | None:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=8)
        if resp.status_code != 200:
            logger.debug("Non-200 status %s for %s", resp.status_code, url)
            return None
        return resp.text
    except requests.RequestException:
        logger.debug("Failed to fetch %s", url)
        return None


def _collect_emails(html: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")

    seen = OrderedDict()

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].strip()
        if href.startswith("mailto:"):
            email = href[7:].split("?")[0]
            if email and email not in seen:
                seen[email] = True

    text = soup.get_text(separator=" ")
    for match in EMAIL_RE.finditer(text):
        email = match.group(0)
        if email not in seen:
            seen[email] = True

    return list(seen)


def _parse_instagram(html: str) -> str | None:
    soup = BeautifulSoup(html, "lxml")
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].strip()
        if "instagram.com" in href:
            return href
    return None


def enrich_business(record: dict) -> dict:
    website = record.get("website")
    if not website:
        return record

    html = _fetch(website)
    if html is None:
        for path in ("/contact", "/about"):
            html = _fetch(website.rstrip("/") + path)
            if html:
                break

    if html is None:
        return record

    record = dict(record)

    emails = _collect_emails(html)
    business_email = None
    personal_email = None
    for email in emails:
        domain = email.split("@")[-1].lower()
        if domain in PERSONAL_EMAIL_DOMAINS:
            if personal_email is None:
                personal_email = email
        else:
            if business_email is None:
                business_email = email

    if business_email is not None:
        record["email"] = business_email
    if personal_email is not None:
        record["personal_email"] = personal_email

    insta = _parse_instagram(html)
    if insta is not None:
        record["instagram_url"] = insta
    return record
