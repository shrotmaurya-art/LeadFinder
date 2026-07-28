import pytest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from crm.database import Database
from utils.timeutil import today_local, now_local_iso
import config

BASE_RECORD = {
    "name": "Test Biz",
    "phone": "+911111111111",
    "normalized_phone": "+911111111111",
    "website": "http://example.com",
    "normalized_website": "http://example.com",
    "city": "Mumbai",
}


@pytest.fixture
def db(tmp_path):
    d = Database(db_path=tmp_path / "test.db")
    d.init_db()
    return d


class TestInsertAndFetch:
    def test_insert_and_find_by_phone(self, db):
        biz_id = db.insert_business(BASE_RECORD)
        row = db.find_by_phone_or_website("+911111111111", None)
        assert row is not None
        assert row["id"] == biz_id
        assert row["name"] == "Test Biz"

    def test_insert_and_find_by_website(self, db):
        biz_id = db.insert_business(BASE_RECORD)
        row = db.find_by_phone_or_website(None, "http://example.com")
        assert row is not None
        assert row["id"] == biz_id

    def test_find_by_phone_or_website_returns_none(self, db):
        assert db.find_by_phone_or_website("+999", None) is None


class TestUniqueConstraints:
    def test_duplicate_phone_raises(self, db):
        db.insert_business(BASE_RECORD)
        dup = dict(BASE_RECORD)
        dup["name"] = "Duplicate"
        with pytest.raises(Exception) as exc:
            db.insert_business(dup)
        assert "UNIQUE" in str(exc.value) or "IntegrityError" in type(exc.value).__name__

    def test_duplicate_website_raises(self, db):
        db.insert_business(BASE_RECORD)
        dup = dict(BASE_RECORD)
        dup["name"] = "Duplicate"
        dup["normalized_phone"] = "+912222222222"
        dup["phone"] = "+912222222222"
        with pytest.raises(Exception) as exc:
            db.insert_business(dup)
        assert "UNIQUE" in str(exc.value) or "IntegrityError" in type(exc.value).__name__

    def test_two_null_phones_allowed(self, db):
        r1 = dict(BASE_RECORD, name="A", normalized_phone=None, phone=None,
                  normalized_website="http://a.com", website="http://a.com")
        r2 = dict(BASE_RECORD, name="B", normalized_phone=None, phone=None,
                  normalized_website="http://b.com", website="http://b.com")
        db.insert_business(r1)
        db.insert_business(r2)

    def test_two_null_websites_allowed(self, db):
        r1 = dict(BASE_RECORD, name="A", normalized_website=None, website=None)
        r2 = dict(BASE_RECORD, name="B", normalized_website=None, website=None,
                  normalized_phone="+912222222222", phone="+912222222222")
        db.insert_business(r1)
        db.insert_business(r2)


class TestStatusUpdate:
    def test_update_status(self, db):
        biz_id = db.insert_business(BASE_RECORD)
        db.update_status(biz_id, "Replied")
        row = db.find_by_phone_or_website("+911111111111", None)
        assert row["status"] == "Replied"


class TestUpdateEmail:
    def test_update_email_persists(self, db):
        biz_id = db.insert_business(BASE_RECORD)
        db.update_email(biz_id, "new@example.com")
        row = db.find_by_phone_or_website("+911111111111", None)
        assert row["email"] == "new@example.com"

    def test_update_email_overwrites_existing(self, db):
        record = dict(BASE_RECORD, email="old@example.com")
        biz_id = db.insert_business(record)
        db.update_email(biz_id, "new@example.com")
        row = db.find_by_phone_or_website("+911111111111", None)
        assert row["email"] == "new@example.com"


class TestOptOut:
    def test_opt_out_persists(self, db):
        biz_id = db.insert_business(BASE_RECORD)
        db.set_opt_out(biz_id, True)
        row = db.find_by_phone_or_website("+911111111111", None)
        assert row["opt_out"] == 1

    def test_opt_out_false(self, db):
        biz_id = db.insert_business(BASE_RECORD)
        db.set_opt_out(biz_id, False)
        row = db.find_by_phone_or_website("+911111111111", None)
        assert row["opt_out"] == 0


class TestFollowUp:
    def test_increment_follow_up(self, db):
        biz_id = db.insert_business(BASE_RECORD)
        db.increment_follow_up(biz_id)
        row = db.find_by_phone_or_website("+911111111111", None)
        assert row["follow_up_count"] == 1
        assert row["last_contacted_date"] == today_local()

    def test_increment_multiple_times(self, db):
        biz_id = db.insert_business(BASE_RECORD)
        db.increment_follow_up(biz_id)
        db.increment_follow_up(biz_id)
        db.increment_follow_up(biz_id)
        row = db.find_by_phone_or_website("+911111111111", None)
        assert row["follow_up_count"] == 3


class TestContactLog:
    def test_log_contact(self, db):
        biz_id = db.insert_business(BASE_RECORD)
        log_id = db.log_contact(biz_id, "whatsapp", "Hello", 1, "bot")
        assert log_id is not None
        assert isinstance(log_id, int)

    def test_log_contact_without_sent_by(self, db):
        biz_id = db.insert_business(BASE_RECORD)
        log_id = db.log_contact(biz_id, "email", "Test", 1, None)
        assert isinstance(log_id, int)


class TestAudit:
    def test_get_latest_audit_returns_most_recent(self, db):
        biz_id = db.insert_business(BASE_RECORD)
        id1 = db.save_audit(biz_id, True, False, False, 3)
        id2 = db.save_audit(biz_id, False, True, True, 10)
        audit = db.get_latest_audit(biz_id)
        assert audit is not None
        assert audit["review_count"] == 10
        assert audit["has_website"] == 0
        assert audit["has_business_email"] == 1
        assert audit["has_instagram"] == 1

    def test_get_latest_audit_no_audits(self, db):
        biz_id = db.insert_business(BASE_RECORD)
        assert db.get_latest_audit(biz_id) is None


class TestDashboardCounts:
    def test_dashboard_counts_mixed(self, db):
        today = today_local()
        yesterday = (datetime.now(ZoneInfo(config.APP_TIMEZONE)) - timedelta(days=1)).date().isoformat()

        r1 = dict(BASE_RECORD, name="Today New", status="New",
                  normalized_phone="+911111111111", first_found_date=today)
        r2 = dict(BASE_RECORD, name="Yesterday Found", status="New",
                  normalized_phone="+912222222222", phone="+912222222222",
                  normalized_website="http://yesterday.com", website="http://yesterday.com",
                  first_found_date=yesterday)
        r3 = dict(BASE_RECORD, name="Ready Biz", status="Ready to Contact",
                  normalized_phone="+913333333333", phone="+913333333333",
                  normalized_website="http://ready.com", website="http://ready.com",
                  first_found_date=today)
        r4 = dict(BASE_RECORD, name="Replied Biz", status="Replied",
                  normalized_phone="+914444444444", phone="+914444444444",
                  normalized_website="http://replied.com", website="http://replied.com",
                  first_found_date=today)
        r5 = dict(BASE_RECORD, name="Meeting Biz", status="Meeting Scheduled",
                  normalized_phone="+915555555555", phone="+915555555555",
                  normalized_website="http://meeting.com", website="http://meeting.com",
                  first_found_date=today)
        r6 = dict(BASE_RECORD, name="Client Biz", status="Client",
                  normalized_phone="+916666666666", phone="+916666666666",
                  normalized_website="http://client.com", website="http://client.com",
                  first_found_date=today)

        ids = {}
        for r in [r1, r2, r3, r4, r5, r6]:
            ids[r["name"]] = db.insert_business(r)

        db.log_contact(ids["Today New"], "whatsapp", "msg", 1, "bot")

        counts = db.get_dashboard_counts(today)
        assert counts["businesses_found_today"] == 5
        assert counts["new_leads"] == 2
        assert counts["messages_ready"] == 1
        assert counts["sent_today"] == 1
        assert counts["replies"] == 1
        assert counts["meetings"] == 1
        assert counts["clients"] == 1


class TestMultiCityFiltering:
    def test_get_leads_by_city_list(self, db):
        db.insert_business(dict(BASE_RECORD, name="A", city="Mumbai"))
        db.insert_business(dict(BASE_RECORD, name="B", city="Virar",
                                normalized_phone="+912222222222", phone="+912222222222",
                                normalized_website="http://b.com", website="http://b.com"))
        db.insert_business(dict(BASE_RECORD, name="C", city="Delhi",
                                normalized_phone="+913333333333", phone="+913333333333",
                                normalized_website="http://c.com", website="http://c.com"))

        results = db.get_leads(city=["Mumbai", "Virar"])
        names = {r["name"] for r in results}
        assert names == {"A", "B"}

    def test_get_leads_by_single_city_string(self, db):
        db.insert_business(dict(BASE_RECORD, name="A", city="Mumbai"))
        db.insert_business(dict(BASE_RECORD, name="B", city="Virar",
                                normalized_phone="+912222222222", phone="+912222222222",
                                normalized_website="http://b.com", website="http://b.com"))

        results = db.get_leads(city="Mumbai")
        assert len(results) == 1
        assert results[0]["name"] == "A"

    def test_get_dashboard_counts_by_city_list(self, db):
        today = today_local()
        db.insert_business(dict(BASE_RECORD, name="M1", city="Mumbai", status="New", first_found_date=today))
        db.insert_business(dict(BASE_RECORD, name="V1", city="Virar", status="New",
                                normalized_phone="+912222222222", phone="+912222222222",
                                normalized_website="http://v1.com", website="http://v1.com",
                                first_found_date=today))
        db.insert_business(dict(BASE_RECORD, name="D1", city="Delhi", status="New",
                                normalized_phone="+913333333333", phone="+913333333333",
                                normalized_website="http://d1.com", website="http://d1.com",
                                first_found_date=today))

        counts = db.get_dashboard_counts(today, city=["Mumbai", "Virar"])
        assert counts["new_leads"] == 2

    def test_get_dashboard_counts_by_single_city_string(self, db):
        today = today_local()
        db.insert_business(dict(BASE_RECORD, name="M1", city="Mumbai", status="New", first_found_date=today))
        db.insert_business(dict(BASE_RECORD, name="V1", city="Virar", status="New",
                                normalized_phone="+912222222222", phone="+912222222222",
                                normalized_website="http://v1.com", website="http://v1.com",
                                first_found_date=today))

        counts = db.get_dashboard_counts(today, city="Mumbai")
        assert counts["new_leads"] == 1


class TestDraftPersistence:
    def test_save_and_get_draft(self, db):
        biz_id = db.insert_business(BASE_RECORD)
        db.save_draft(biz_id, "Subj", "Body text", "WA msg")
        draft = db.get_draft(biz_id)
        assert draft is not None
        assert draft["draft_email_subject"] == "Subj"
        assert draft["draft_email_body"] == "Body text"
        assert draft["draft_whatsapp_message"] == "WA msg"

    def test_get_draft_returns_none_when_empty(self, db):
        biz_id = db.insert_business(BASE_RECORD)
        assert db.get_draft(biz_id) is None

    def test_save_draft_overwrites_previous(self, db):
        biz_id = db.insert_business(BASE_RECORD)
        db.save_draft(biz_id, "v1", "body1", "wa1")
        db.save_draft(biz_id, "v2", "body2", "wa2")
        draft = db.get_draft(biz_id)
        assert draft["draft_email_subject"] == "v2"
        assert draft["draft_email_body"] == "body2"
        assert draft["draft_whatsapp_message"] == "wa2"

    def test_clear_draft_email(self, db):
        biz_id = db.insert_business(BASE_RECORD)
        db.save_draft(biz_id, "Subj", "Body", "WA msg")
        db.clear_draft(biz_id, "email")
        draft = db.get_draft(biz_id)
        # Email columns cleared, WhatsApp still present
        assert draft["draft_email_subject"] is None
        assert draft["draft_email_body"] is None
        assert draft["draft_whatsapp_message"] == "WA msg"

    def test_clear_draft_whatsapp(self, db):
        biz_id = db.insert_business(BASE_RECORD)
        db.save_draft(biz_id, "Subj", "Body", "WA msg")
        db.clear_draft(biz_id, "whatsapp")
        draft = db.get_draft(biz_id)
        assert draft["draft_email_subject"] == "Subj"
        assert draft["draft_whatsapp_message"] is None

    def test_clear_draft_both_returns_none(self, db):
        biz_id = db.insert_business(BASE_RECORD)
        db.save_draft(biz_id, "Subj", "Body", "WA msg")
        db.clear_draft(biz_id, "email")
        db.clear_draft(biz_id, "whatsapp")
        assert db.get_draft(biz_id) is None

    def test_clear_draft_invalid_channel_raises(self, db):
        biz_id = db.insert_business(BASE_RECORD)
        with pytest.raises(ValueError, match="Unsupported channel"):
            db.clear_draft(biz_id, "sms")

    def test_init_db_idempotent_with_draft_columns(self, db):
        """Re-running init_db on an existing DB should not error."""
        db.init_db()
        db.init_db()
        biz_id = db.insert_business(BASE_RECORD)
        db.save_draft(biz_id, "s", "b", "w")
        assert db.get_draft(biz_id) is not None
