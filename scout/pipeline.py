import config
from scout.search import PlaywrightMapsSource
from scout.extract import enrich_business
from scout.deduplicate import is_duplicate
from scout.normalize import normalize_phone, normalize_website, normalize_address
from crm.database import Database
from utils.logger import get_logger

logger = get_logger(__name__)


def run_scout(city: str, category: str, db: Database) -> dict:
    if config.DATA_SOURCE == "playwright":
        source = PlaywrightMapsSource()
    else:
        from scout.places_api import PlacesAPISource
        source = PlacesAPISource()

    raw_results = source.search(city, category)

    new = 0
    duplicates = 0

    for record in raw_results:
        try:
            original_email = record.get("email")
            original_insta = record.get("instagram_url")

            record = enrich_business(record)

            if original_email:
                record["email"] = original_email
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
