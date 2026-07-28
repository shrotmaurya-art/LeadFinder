import pytest

import config
from crm.database import Database
from crm.leads import OptedOutError
from outreach import sender
from outreach.sender import MissingEmailError


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

    with pytest.raises(MissingEmailError, match="No business email on file"):
        sender.prepare_send(
            {"id": business_id, "opt_out": 0, "email": None},
            "email",
            "sub",
            "body",
        )


def test_prepare_send_blocks_when_email_cap_reached(sender_db):
    business_id = sender_db.insert_business({"name": "Capped", "opt_out": 0, "email": "a@b.com"})
    for _ in range(config.EMAIL_DAILY_CAP):
        sender_db.log_contact(business_id, "email", "msg", 0, "me")

    result = sender.prepare_send(
        {"id": business_id, "opt_out": 0, "email": "a@b.com"},
        "email",
        "sub",
        "does-not-matter",
    )

    assert result == {"blocked": True, "reason": "Daily email limit reached"}


def test_prepare_send_gmail_web_builds_gmail_compose_url(sender_db, monkeypatch):
    monkeypatch.setattr(config, "EMAIL_LINK_STYLE", "gmail_web")
    business_id = sender_db.insert_business({"name": "Gmail Lead"})

    result = sender.prepare_send(
        {"id": business_id, "opt_out": 0, "email": "test@example.com"},
        "email",
        "Hello",
        "Body text",
    )

    assert result["blocked"] is False
    assert result["link"].startswith("https://mail.google.com/mail/?view=cm&fs=1")
    assert "to=test%40example.com" in result["link"]
    assert "su=Hello" in result["link"]
    assert "body=Body%20text" in result["link"]


def test_prepare_send_gmail_web_copy_fallback_for_long_message(sender_db, monkeypatch):
    monkeypatch.setattr(config, "EMAIL_LINK_STYLE", "gmail_web")
    business_id = sender_db.insert_business({"name": "Long Gmail"})

    result = sender.prepare_send(
        {"id": business_id, "opt_out": 0, "email": "a@b.com"},
        "email",
        "sub",
        "x" * 2000,
    )

    assert result == {"blocked": False, "link": None, "fallback": "copy"}


def test_prepare_send_mailto_by_default(sender_db, monkeypatch):
    monkeypatch.setattr(config, "EMAIL_LINK_STYLE", "mailto")
    business_id = sender_db.insert_business({"name": "Mailto Lead"})

    result = sender.prepare_send(
        {"id": business_id, "opt_out": 0, "email": "a@b.com"},
        "email",
        "sub",
        "body",
    )

    assert result["blocked"] is False
    assert result["link"].startswith("mailto:")
