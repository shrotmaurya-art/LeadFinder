import pytest

from crm.database import Database
from crm.leads import OptedOutError
from outreach import sender


@pytest.fixture
def sender_db(tmp_path, monkeypatch):
    database = Database(tmp_path / "sender.db")
    database.init_db()
    monkeypatch.setattr(sender, "db", database)
    return database


def test_to_whatsapp_link_format_removes_plus_and_non_digits():
    assert sender.to_whatsapp_link_format("+91 (987) 654-3210") == "919876543210"


def test_prepare_send_blocks_opted_out_business(sender_db):
    business_id = sender_db.insert_business({"name": "Opted Out", "opt_out": 1})

    with pytest.raises(OptedOutError):
        sender.prepare_send(
            {"id": business_id, "opt_out": 1, "email": "a@b.com"},
            "email",
            "sub",
            "body",
        )


def test_prepare_send_returns_copy_fallback_for_long_email(sender_db):
    business_id = sender_db.insert_business({"name": "Long Email"})

    result = sender.prepare_send(
        {"id": business_id, "opt_out": 0, "email": "a@b.com"},
        "email",
        "sub",
        "x" * 2000,
    )

    assert result == {"blocked": False, "link": None, "fallback": "copy"}


def test_prepare_send_blocks_missing_email(sender_db):
    business_id = sender_db.insert_business({"name": "No Email"})

    result = sender.prepare_send(
        {"id": business_id, "opt_out": 0, "email": None},
        "email",
        "sub",
        "body",
    )

    assert result == {"blocked": True, "reason": "No business email on file"}
