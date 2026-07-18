"""Cost-conscious Google Places API (New) data source.

The Places API bills by requested field.  Rating, review count, and website
are Enterprise-tier fields, so this source deliberately omits them unless
``INCLUDE_RATINGS_VIA_API`` is explicitly enabled.  Cached raw responses also
avoid repeat API calls (and quota consumption) for 24 hours.
"""

import hashlib
import json
import time
from pathlib import Path

import requests

import config
from scout.base import BusinessDataSource
from scout.normalize import normalize_address, normalize_phone, normalize_website
from utils.logger import get_logger


logger = get_logger(__name__)

SEARCH_TEXT_URL = "https://places.googleapis.com/v1/places:searchText"
CACHE_TTL_SECONDS = 24 * 60 * 60
BASE_FIELDS = [
    "places.id",
    "places.displayName",
    "places.formattedAddress",
    "places.nationalPhoneNumber",
    "places.internationalPhoneNumber",
]
RATING_FIELDS = [
    "places.rating",
    "places.userRatingCount",
    "places.websiteUri",
]
CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "cache"


class PlacesAPISource(BusinessDataSource):
    """Retrieve business leads from Google Places API (New)."""

    def __init__(self) -> None:
        if config.DATA_SOURCE == "places_api" and not config.GOOGLE_PLACES_API_KEY:
            raise ValueError(
                "DATA_SOURCE=places_api requires GOOGLE_PLACES_API_KEY. "
                "Add a billing-enabled Google Cloud API key to .env, or use "
                "DATA_SOURCE=playwright."
            )

    def search(self, city: str, category: str) -> list[dict]:
        """Search for businesses, using a 24-hour raw-response cache."""
        response_data = self._load_cached_response(city, category)
        if response_data is None:
            response_data = self._request_places(city, category)
            self._cache_response(city, category, response_data)

        return [self._to_business_record(place, city, category) for place in response_data.get("places", [])]

    def _request_places(self, city: str, category: str) -> dict:
        field_mask = self._field_mask()
        logger.info("X-Goog-FieldMask: %s", field_mask)
        response = requests.post(
            SEARCH_TEXT_URL,
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": config.GOOGLE_PLACES_API_KEY,
                "X-Goog-FieldMask": field_mask,
            },
            json={"textQuery": f"{category} in {city}"},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def _field_mask(self) -> str:
        fields = BASE_FIELDS.copy()
        if config.INCLUDE_RATINGS_VIA_API:
            fields.extend(RATING_FIELDS)
        return ",".join(fields)

    def _cache_path(self, city: str, category: str) -> Path:
        cache_key = hashlib.sha256(f"{city}\n{category}".encode("utf-8")).hexdigest()
        return CACHE_DIR / f"places_{cache_key}.json"

    def _load_cached_response(self, city: str, category: str) -> dict | None:
        cache_path = self._cache_path(city, category)
        if not cache_path.exists() or time.time() - cache_path.stat().st_mtime >= CACHE_TTL_SECONDS:
            return None

        try:
            with cache_path.open(encoding="utf-8") as cache_file:
                cached_response = json.load(cache_file)
        except (OSError, json.JSONDecodeError) as error:
            logger.warning("Unable to read Places API cache %s: %s", cache_path, error)
            return None

        if not isinstance(cached_response, dict):
            logger.warning("Ignoring invalid Places API cache %s", cache_path)
            return None

        logger.info("Using cached Places API response: %s", cache_path)
        return cached_response

    def _cache_response(self, city: str, category: str, response_data: dict) -> None:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_path = self._cache_path(city, category)
        try:
            with cache_path.open("w", encoding="utf-8") as cache_file:
                json.dump(response_data, cache_file)
        except OSError as error:
            logger.warning("Unable to cache Places API response at %s: %s", cache_path, error)

    @staticmethod
    def _to_business_record(place: dict, city: str, category: str) -> dict:
        display_name = place.get("displayName") or {}
        name = display_name.get("text", "") if isinstance(display_name, dict) else ""
        address = normalize_address(place.get("formattedAddress"))
        phone = place.get("internationalPhoneNumber")
        website = place.get("websiteUri")

        return {
            "name": name,
            "phone": phone,
            "normalized_phone": normalize_phone(phone),
            "website": website,
            "normalized_website": normalize_website(website),
            "email": None,
            "instagram_url": None,
            "address": address,
            "city": city,
            "category": category,
            "google_rating": place.get("rating"),
            "google_reviews_count": place.get("userRatingCount"),
            "source_url": None,
        }
