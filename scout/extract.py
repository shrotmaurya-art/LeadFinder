import re
import requests
from bs4 import BeautifulSoup
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
        resp.raise_for_status()
        return resp.text
    except requests.RequestException:
        logger.debug("Failed to fetch %s", url)
        return None


def _parse_email(html: str) -> str | None:
    soup = BeautifulSoup(html, "lxml")
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].strip()
        if href.startswith("mailto:"):
            email = href[7:].split("?")[0]
            if email:
                return email
    text = soup.get_text(separator=" ")
    match = EMAIL_RE.search(text)
    return match.group(0) if match else None


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
    email = _parse_email(html)
    if email is not None:
        record["email"] = email
    insta = _parse_instagram(html)
    if insta is not None:
        record["instagram_url"] = insta
    return record
