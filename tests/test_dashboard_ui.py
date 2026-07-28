import pytest
from crm.database import Database
from crm.leads import STATUS_FLOW, InvalidStatusTransitionError, transition_status
from analyzer.recommendations import recommend_services
from outreach import sender


@pytest.fixture
def dashboard_db(tmp_path, monkeypatch):
    database = Database(tmp_path / "dashboard.db")
    database.init_db()
    monkeypatch.setattr(sender, "db", database)
    return database


def test_leads_to_review_ordering_and_recommendations(dashboard_db):
    biz1 = dashboard_db.insert_business({
        "name": "Alpha Corp",
        "category": "Tech",
        "status": "Ready to Contact",
        "lead_score": 80,
    })
    biz2 = dashboard_db.insert_business({
        "name": "Beta Inc",
        "category": "Retail",
        "status": "Ready to Contact",
        "lead_score": 95,
    })
    # Not ready to contact
    dashboard_db.insert_business({
        "name": "Gamma LLC",
        "category": "Tech",
        "status": "New",
        "lead_score": 90,
    })

    # Save audits
    dashboard_db.save_audit(biz1, has_website=False, has_business_email=True, has_instagram=True, review_count=5)
    dashboard_db.save_audit(biz2, has_website=True, has_business_email=False, has_instagram=False, review_count=10)

    leads = dashboard_db.get_leads(status="Ready to Contact", order_by_score=True)
    assert len(leads) == 2
    # Ordered by score DESC: Beta Inc (95) then Alpha Corp (80)
    assert leads[0]["name"] == "Beta Inc"
    assert leads[1]["name"] == "Alpha Corp"

    audit_beta = dashboard_db.get_latest_audit(biz2)
    recs_beta = recommend_services(audit_beta)
    assert recs_beta[0] == "Business Email Setup"

    audit_alpha = dashboard_db.get_latest_audit(biz1)
    recs_alpha = recommend_services(audit_alpha)
    assert recs_alpha[0] == "Website"


def test_sender_integration_and_confirm_sent_edited_text(dashboard_db):
    biz_id = dashboard_db.insert_business({
        "name": "Delta Shop",
        "category": "Services",
        "status": "Ready to Contact",
        "phone": "9876543210",
        "normalized_phone": "+919876543210",
        "email": "info@deltashop.com",
        "follow_up_count": 0,
    })

    business = dashboard_db.find_by_phone_or_website("+919876543210", None)
    assert business["id"] == biz_id

    # 1. Prepare Send Email
    prep_email = sender.prepare_send(business, "email", "Custom Subject", "Edited Email Body")
    assert prep_email["blocked"] is False
    assert "mailto:info@deltashop.com" in prep_email["link"]

    # 2. Confirm Sent Email with edited text
    edited_body = "Edited Email Body from User Text Area"
    contact_id = sender.confirm_sent(
        business_id=biz_id,
        channel="email",
        message=edited_body,
        follow_up_number=business["follow_up_count"],
        sent_by="dashboard_user",
    )
    assert contact_id > 0

    # Verify status changed to Contacted and follow_up_count incremented
    updated_biz = dashboard_db.find_by_phone_or_website("+919876543210", None)
    assert updated_biz["status"] == "Contacted"
    assert updated_biz["follow_up_count"] == 1

    # Verify contact log recorded edited_body
    with dashboard_db._connect() as conn:
        row = conn.execute("SELECT * FROM contact_log WHERE id = ?", (contact_id,)).fetchone()
        assert row["message_text"] == edited_body
        assert row["channel"] == "email"
        assert row["follow_up_number"] == 0


def test_pipeline_valid_transitions_are_restricted(dashboard_db):
    """Verify that the selectbox options the pipeline would offer for each
    status are limited to exactly the successors defined in STATUS_FLOW."""
    biz_id = dashboard_db.insert_business({
        "name": "Pipeline Test Co",
        "category": "Tech",
        "status": "New",
        "lead_score": 50,
    })

    business = dashboard_db.get_leads(status="New")[0]
    current = business["status"]
    valid_next = sorted(STATUS_FLOW.get(current, set()))

    # "New" can only go to "Ready to Contact" or "Closed"
    assert valid_next == ["Closed", "Ready to Contact"]

    # Simulate the user picking "Ready to Contact" from the selectbox
    transition_status(biz_id, "Ready to Contact", dashboard_db)
    updated = dashboard_db.get_leads(status="Ready to Contact")
    assert any(b["id"] == biz_id for b in updated)

    # Now from "Ready to Contact" the valid set changes
    current = "Ready to Contact"
    valid_next = sorted(STATUS_FLOW.get(current, set()))
    assert valid_next == ["Closed", "Contacted"]

    # An invalid transition must be rejected
    with pytest.raises(InvalidStatusTransitionError):
        transition_status(biz_id, "New", dashboard_db)

    # Closed is terminal -- no transitions allowed
    transition_status(biz_id, "Closed", dashboard_db)
    assert STATUS_FLOW["Closed"] == set()

    # Confirm the lead is now Closed
    with dashboard_db._connect() as conn:
        row = conn.execute("SELECT status FROM businesses WHERE id = ?", (biz_id,)).fetchone()
        assert row["status"] == "Closed"


def test_pipeline_groups_leads_by_status(dashboard_db):
    """Verify that get_leads(status=X) returns only leads in that status,
    which is the query the pipeline tab uses per column."""
    dashboard_db.insert_business({"name": "A", "status": "New", "lead_score": 10})
    dashboard_db.insert_business({"name": "B", "status": "New", "lead_score": 20})
    dashboard_db.insert_business({"name": "C", "status": "Ready to Contact", "lead_score": 30})
    dashboard_db.insert_business({"name": "D", "status": "Contacted", "lead_score": 40})

    new_leads = dashboard_db.get_leads(status="New", order_by_score=True)
    assert len(new_leads) == 2
    assert new_leads[0]["name"] == "B"  # higher score first

    ready_leads = dashboard_db.get_leads(status="Ready to Contact")
    assert len(ready_leads) == 1
    assert ready_leads[0]["name"] == "C"

    contacted_leads = dashboard_db.get_leads(status="Contacted")
    assert len(contacted_leads) == 1

    client_leads = dashboard_db.get_leads(status="Client")
    assert len(client_leads) == 0
