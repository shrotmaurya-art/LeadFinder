import sys
from pathlib import Path

# Ensure project root is on sys.path when script is executed directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config

from analyzer.audit import run_audit
from analyzer.recommendations import recommend_services
from analyzer.scorer import score_lead
from crm.database import Database
from crm.followups import get_followup_candidates
from crm.leads import transition_status
from outreach import email_generator, whatsapp_generator
from scout import pipeline
from scripts import backup_db, preflight_check
from utils.logger import get_logger
from utils.notify import send_desktop_notification, send_email_notification
from utils.timeutil import today_local

logger = get_logger(__name__)


def run_pipeline(db: Database) -> dict:
    """Run the full daily scout pipeline on an initialised Database.

    Returns a summary dict with keys: found, new, duplicates, messages_ready.
    """
    # 1. Backup database before any writes
    backup_db.run(db.db_path)

    # 2. Scout configured categories across all cities
    total_found = 0
    total_new = 0
    total_duplicates = 0

    for city in config.CITIES:
        res = pipeline.run_scout_city(city, config.CATEGORIES, db)

        total_found += res.get("found", 0)
        total_new += res.get("new", 0)
        total_duplicates += res.get("duplicates", 0)

        logger.info(
            "City %s complete. Found: %d, New: %d, Duplicates: %d",
            city,
            res.get("found", 0),
            res.get("new", 0),
            res.get("duplicates", 0),
        )

    logger.info(
        "Scout complete. Found: %d, New: %d, Duplicates: %d",
        total_found,
        total_new,
        total_duplicates,
    )

    # 3. Audit, score, and draft for New leads
    new_leads = db.get_leads(status="New")
    for biz in new_leads:
        audit = run_audit(biz, db)
        score = score_lead(audit, biz)
        db.update_lead_score(biz["id"], score)
        recs = recommend_services(audit)

        if score >= config.LEAD_SCORE_THRESHOLD:
            email_draft = email_generator.generate_email(
                biz, audit, recs, follow_up_number=0
            )
            wa_draft = whatsapp_generator.generate_whatsapp(
                biz, audit, recs, follow_up_number=0
            )
            db.save_draft(
                biz["id"],
                email_draft.get("subject"),
                email_draft.get("body"),
                wa_draft,
            )
            transition_status(biz["id"], "Ready to Contact", db)

    # 4. Follow-up candidates
    candidates = get_followup_candidates(db)
    for biz in candidates:
        audit = db.get_latest_audit(biz["id"])
        recs = recommend_services(audit) if audit else []
        follow_up_num = biz.get("follow_up_count", 0) + 1
        email_generator.generate_email(
            biz, audit or {}, recs, follow_up_number=follow_up_num
        )
        whatsapp_generator.generate_whatsapp(
            biz, audit or {}, recs, follow_up_number=follow_up_num
        )

    # 5. Collect summary
    date_label = today_local()
    counts = db.get_dashboard_counts(date_label)

    summary = {
        "found": total_found,
        "new": total_new,
        "duplicates": total_duplicates,
        "messages_ready": counts["messages_ready"],
    }
    return summary


def main() -> int:
    # Preflight check
    ok, failures = preflight_check.run()
    if not ok:
        print("[FAIL] Preflight check failed:")
        for reason in failures:
            print(f"  - {reason}")
        return 1

    db = Database()
    db.init_db()

    # Guard: skip if today's scout already ran (e.g. via dashboard trigger)
    last = db.get_last_scout_date()
    today = today_local()
    if last == today:
        print(f"[SKIP] Scout already ran today ({today}), skipping pipeline")
        return 0

    summary = run_pipeline(db)
    db.set_last_scout_date(today)

    # Print final summary using dashboard metric names and today_local()
    date_label = today_local()
    counts = db.get_dashboard_counts(date_label)

    card_defs = [
        ("Businesses Found Today", counts["businesses_found_today"]),
        ("New Leads", counts["new_leads"]),
        ("Messages Ready", counts["messages_ready"]),
        ("Sent Today", counts["sent_today"]),
        ("Replies", counts["replies"]),
        ("Meetings", counts["meetings"]),
        ("Clients", counts["clients"]),
    ]

    print(f"\nLeadFinder Daily Summary ({date_label}):")
    for label, value in card_defs:
        print(f"  {label}: {value}")

    if config.ENABLE_EMAIL_NOTIFY:
        send_email_notification(summary)
    if config.ENABLE_DESKTOP_NOTIFY:
        send_desktop_notification(summary)

    return 0


if __name__ == "__main__":
    sys.exit(main())
