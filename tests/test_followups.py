import pytest
from datetime import date, timedelta

import config
from crm.database import Database
from crm.followups import enforce_daily_cap, get_followup_candidates
from utils.timeutil import today_local


@pytest.fixture
def db(tmp_path):
    d = Database(db_path=tmp_path / "test.db")
    d.init_db()
    return d


class TestEnforceDailyCap:
    def test_under_cap_returns_false(self, db):
        assert enforce_daily_cap("email", db) is False

    def test_unsupported_channel_raises(self, db):
        with pytest.raises(ValueError, match="Unsupported outreach channel"):
            enforce_daily_cap("sms", db)


def _seed_five_businesses(db, monkeypatch):
    """Seed exactly 5 businesses: only one qualifies for follow-up."""
    monkeypatch.setattr(config, "COOLDOWN_DAYS", 15)
    monkeypatch.setattr(config, "MAX_FOLLOW_UPS", 2)

    today = date.fromisoformat(today_local())
    lc_20 = (today - timedelta(days=20)).isoformat()
    lc_5 = (today - timedelta(days=5)).isoformat()

    # 1. Wrong status (Replied) -- excluded
    db.insert_business({
        "name": "Replied Biz",
        "phone": "+911000000001",
        "normalized_phone": "+911000000001",
        "status": "Replied",
        "opt_out": 0,
        "follow_up_count": 0,
        "last_contacted_date": lc_20,
    })
    # 2. Opted out -- excluded
    db.insert_business({
        "name": "Opted Out",
        "phone": "+911000000002",
        "normalized_phone": "+911000000002",
        "status": "Contacted",
        "opt_out": 1,
        "follow_up_count": 0,
        "last_contacted_date": lc_20,
    })
    # 3. At max follow-ups -- excluded
    db.insert_business({
        "name": "Maxed Out",
        "phone": "+911000000003",
        "normalized_phone": "+911000000003",
        "status": "Contacted",
        "opt_out": 0,
        "follow_up_count": 2,
        "last_contacted_date": lc_20,
    })
    # 4. Too recent (5 days) -- excluded
    db.insert_business({
        "name": "Too Recent",
        "phone": "+911000000004",
        "normalized_phone": "+911000000004",
        "status": "Contacted",
        "opt_out": 0,
        "follow_up_count": 0,
        "last_contacted_date": lc_5,
    })
    # 5. Qualifying -- included
    qualifying_id = db.insert_business({
        "name": "Qualifying Biz",
        "phone": "+911000000005",
        "normalized_phone": "+911000000005",
        "status": "Contacted",
        "opt_out": 0,
        "follow_up_count": 0,
        "last_contacted_date": lc_20,
    })
    return qualifying_id


def test_candidates(db, monkeypatch):
    """Seed 5 businesses; only the one qualifying Contacted lead is returned."""
    qualifying_id = _seed_five_businesses(db, monkeypatch)

    candidates = get_followup_candidates(db)

    assert len(candidates) == 1
    assert candidates[0]["id"] == qualifying_id
    assert candidates[0]["name"] == "Qualifying Biz"

    # Verify status was persisted
    with db._connect() as conn:
        row = conn.execute(
            "SELECT status FROM businesses WHERE id = ?", (qualifying_id,)
        ).fetchone()
    assert row["status"] == "Ready to Contact"


def test_idempotent(db, monkeypatch):
    """Calling get_followup_candidates twice does not duplicate or re-increment."""
    qualifying_id = _seed_five_businesses(db, monkeypatch)

    first = get_followup_candidates(db)
    assert len(first) == 1

    # Second call: the business is now 'Ready to Contact', so excluded by SQL
    second = get_followup_candidates(db)
    assert len(second) == 0

    # follow_up_count was NOT incremented by get_followup_candidates
    with db._connect() as conn:
        row = conn.execute(
            "SELECT follow_up_count FROM businesses WHERE id = ?", (qualifying_id,)
        ).fetchone()
    assert row["follow_up_count"] == 0


def test_cooldown_boundary(db, monkeypatch):
    """Exactly at cooldown threshold is included (>=)."""
    monkeypatch.setattr(config, "COOLDOWN_DAYS", 15)
    monkeypatch.setattr(config, "MAX_FOLLOW_UPS", 2)

    today = date.fromisoformat(today_local())
    lc_exact = (today - timedelta(days=15)).isoformat()
    db.insert_business({
        "name": "Boundary Biz",
        "phone": "+911000000010",
        "normalized_phone": "+911000000010",
        "status": "Contacted",
        "opt_out": 0,
        "follow_up_count": 0,
        "last_contacted_date": lc_exact,
    })

    assert len(get_followup_candidates(db)) == 1


def test_null_last_contacted_excluded(db, monkeypatch):
    """Business with NULL last_contacted_date is excluded."""
    monkeypatch.setattr(config, "COOLDOWN_DAYS", 15)
    monkeypatch.setattr(config, "MAX_FOLLOW_UPS", 2)

    db.insert_business({
        "name": "Never Contacted",
        "phone": "+911000000011",
        "normalized_phone": "+911000000011",
        "status": "Contacted",
        "opt_out": 0,
        "follow_up_count": 0,
        "last_contacted_date": None,
    })

    assert len(get_followup_candidates(db)) == 0


def test_empty_result_logs(db, monkeypatch, caplog):
    """No candidates produces an info-level log message."""
    monkeypatch.setattr(config, "COOLDOWN_DAYS", 15)
    monkeypatch.setattr(config, "MAX_FOLLOW_UPS", 2)

    with caplog.at_level("INFO"):
        get_followup_candidates(db)

    assert "No follow-up candidates found" in caplog.text
