import pytest
from unittest.mock import MagicMock
from crm.database import Database
from scripts import run_daily, preflight_check, backup_db
from scout import pipeline


@pytest.fixture
def run_daily_db(tmp_path, monkeypatch):
    test_db = Database(tmp_path / "run_daily.db")
    test_db.init_db()
    monkeypatch.setattr(run_daily, "Database", lambda: test_db)
    return test_db


def test_run_daily_preflight_failure(monkeypatch):
    monkeypatch.setattr(preflight_check, "run", lambda: (False, ["Ollama unreachable"]))
    exit_code = run_daily.main()
    assert exit_code == 1


def test_run_daily_full_workflow(run_daily_db, monkeypatch, capsys):
    # Mock preflight check to pass
    monkeypatch.setattr(preflight_check, "run", lambda: (True, []))

    # Mock backup_db
    backup_mock = MagicMock()
    monkeypatch.setattr(backup_db, "run", backup_mock)

    # Mock config
    monkeypatch.setattr(run_daily.config, "CATEGORIES", ["Gym"])
    monkeypatch.setattr(run_daily.config, "CITIES", ["TestCity"])
    monkeypatch.setattr(run_daily.config, "LEAD_SCORE_THRESHOLD", 40)

    # Seed business into DB as part of scout pipeline mock
    def mock_run_scout_city(city, categories, db):
        db.insert_business({
            "name": "High Score Gym",
            "category": "Gym",
            "city": city,
            "status": "New",
            "google_reviews_count": 5,
        })
        return {"found": 1, "new": 1, "duplicates": 0}

    monkeypatch.setattr(pipeline, "run_scout_city", mock_run_scout_city)

    # Mock LLM generators to avoid calling external API during test
    monkeypatch.setattr(run_daily.email_generator, "generate_email", lambda b, a, r, follow_up_number=0: {"subject": "Sub", "body": "Body"})
    monkeypatch.setattr(run_daily.whatsapp_generator, "generate_whatsapp", lambda b, a, r, follow_up_number=0: "WA Draft")

    exit_code = run_daily.main()
    assert exit_code == 0
    assert backup_mock.called

    # Verify business was audited, scored, and transitioned to Ready to Contact
    leads = run_daily_db.get_leads(status="Ready to Contact")
    assert len(leads) == 1
    assert leads[0]["name"] == "High Score Gym"
    assert leads[0]["lead_score"] > 0

    # Verify summary output
    captured = capsys.readouterr().out
    assert "LeadFinder Daily Summary" in captured
    assert "Businesses Found Today: 1" in captured
    assert "New Leads: 0" in captured


def test_run_daily_saves_draft_when_score_above_threshold(run_daily_db, monkeypatch):
    """Drafts must be persisted to DB when a lead crosses LEAD_SCORE_THRESHOLD."""
    monkeypatch.setattr(preflight_check, "run", lambda: (True, []))
    monkeypatch.setattr(backup_db, "run", lambda *a, **kw: None)
    monkeypatch.setattr(run_daily.config, "CATEGORIES", ["Cafe"])
    monkeypatch.setattr(run_daily.config, "CITIES", ["Town"])
    monkeypatch.setattr(run_daily.config, "LEAD_SCORE_THRESHOLD", 10)

    def mock_run_scout_city(city, categories, db):
        db.insert_business({
            "name": "Cafe Mocha",
            "category": "Cafe",
            "city": city,
            "status": "New",
            "google_reviews_count": 20,
        })
        return {"found": 1, "new": 1, "duplicates": 0}

    monkeypatch.setattr(pipeline, "run_scout_city", mock_run_scout_city)
    monkeypatch.setattr(run_daily.email_generator, "generate_email",
                        lambda b, a, r, follow_up_number=0: {"subject": "Hi", "body": "Hello there"})
    monkeypatch.setattr(run_daily.whatsapp_generator, "generate_whatsapp",
                        lambda b, a, r, follow_up_number=0: "WhatsApp hello")

    assert run_daily.main() == 0

    leads = run_daily_db.get_leads(status="Ready to Contact")
    assert len(leads) == 1
    draft = run_daily_db.get_draft(leads[0]["id"])
    assert draft is not None
    assert draft["draft_email_subject"] == "Hi"
    assert draft["draft_email_body"] == "Hello there"
    assert draft["draft_whatsapp_message"] == "WhatsApp hello"

