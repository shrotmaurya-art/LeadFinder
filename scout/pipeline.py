import config
from scout.search import PlaywrightMapsSource
from scout.extract import enrich_business
from scout.deduplicate import is_duplicate
from scout.normalize import normalize_phone, normalize_website, normalize_address
from crm.database import Database
from utils.logger import get_logger

logger = get_logger(__name__)


def _process_records(raw_results: list[dict], db: Database) -> dict:
    """Enrich, deduplicate, and insert a batch of raw records. Returns counts."""
    new = 0
    duplicates = 0

    for record in raw_results:
        try:
            original_email = record.get("email")
            original_personal_email = record.get("personal_email")
            original_insta = record.get("instagram_url")

            record = enrich_business(record)

            if original_email:
                record["email"] = original_email
            if original_personal_email:
                record["personal_email"] = original_personal_email
            if original_insta:
                record["instagram_url"] = original_insta

            record["normalized_phone"] = normalize_phone(record.get("phone"))
            record["normalized_website"] = normalize_website(record.get("website"))
            record["normalized_address"] = normalize_address(record.get("address"))

            dup, dup_id = is_duplicate(record, db)
            if dup:
                db.touch_last_seen(dup_id)
                duplicates += 1
            else:
                insert_record = {k: v for k, v in record.items() if k != "normalized_address"}
                db.insert_business(insert_record)
                new += 1

        except Exception as e:
            logger.error(
                "Failed to process record name=%s phone=%s: %s",
                record.get("name"),
                record.get("phone"),
                e,
                exc_info=True,
            )
            continue

    return {"found": len(raw_results), "new": new, "duplicates": duplicates}


def run_scout(city: str, category: str, db: Database) -> dict:
    if config.DATA_SOURCE == "playwright":
        source = PlaywrightMapsSource()
    else:
        from scout.places_api import PlacesAPISource
        source = PlacesAPISource()

    raw_results = source.search(city, category)
    return _process_records(raw_results, db)


def run_scout_city(city: str, categories: list[str], db: Database) -> dict:
    """Scout all categories for a city using a single browser session.

    Falls back to per-category search for non-playwright data sources.
    Returns aggregate counts: found, new, duplicates.
    """
    if config.DATA_SOURCE == "playwright":
        source = PlaywrightMapsSource()
        batch = source.search_city(city, categories)
        all_results = []
        for cat_results in batch.values():
            all_results.extend(cat_results)
    else:
        from scout.places_api import PlacesAPISource
        source = PlacesAPISource()
        all_results = []
        for category in categories:
            all_results.extend(source.search(city, category))

    return _process_records(all_results, db)
