"""Tests for crm_service — Revenue CRM Lite."""

from products.fred_assistant.services import crm_service


def test_create_lead():
    lead = crm_service.create_lead({"name": "John Smith", "company": "Acme Corp", "email": "john@acme.com", "deal_value": 5000})
    assert lead["name"] == "John Smith"
    assert lead["company"] == "Acme Corp"
    assert lead["pipeline_stage"] == "cold"
    assert lead["deal_value"] == 5000


def test_get_lead():
    lead = crm_service.create_lead({"name": "Jane Doe"})
    fetched = crm_service.get_lead(lead["id"])
    assert fetched["name"] == "Jane Doe"


def test_get_lead_not_found():
    assert crm_service.get_lead("nonexistent") is None


def test_update_lead():
    lead = crm_service.create_lead({"name": "Bob", "deal_value": 1000})
    updated = crm_service.update_lead(lead["id"], {"pipeline_stage": "contacted", "deal_value": 2000})
    assert updated["pipeline_stage"] == "contacted"
    assert updated["deal_value"] == 2000


def test_delete_lead():
    lead = crm_service.create_lead({"name": "Delete Me"})
    crm_service.delete_lead(lead["id"])
    assert crm_service.get_lead(lead["id"]) is None


def test_list_leads():
    crm_service.create_lead({"name": "A", "pipeline_stage": "cold"})
    crm_service.create_lead({"name": "B", "pipeline_stage": "contacted"})
    all_leads = crm_service.list_leads()
    assert len(all_leads) == 2
    cold_leads = crm_service.list_leads(stage="cold")
    assert len(cold_leads) == 1


def test_log_outreach():
    lead = crm_service.create_lead({"name": "Test Lead"})
    entry = crm_service.log_outreach(lead["id"], "email", "Hey there!", "no reply")
    assert entry["lead_id"] == lead["id"]
    assert entry["outreach_type"] == "email"


def test_get_outreach_history():
    lead = crm_service.create_lead({"name": "Test"})
    crm_service.log_outreach(lead["id"], "email", "First email")
    crm_service.log_outreach(lead["id"], "call", "Follow-up call")
    history = crm_service.get_outreach_history(lead["id"])
    assert len(history) == 2


def test_schedule_followup():
    lead = crm_service.create_lead({"name": "Follow Up Lead"})
    result = crm_service.schedule_followup(lead["id"], "2026-03-01", "Check in about trial")
    assert result["next_followup"] == "2026-03-01"


def test_move_lead():
    lead = crm_service.create_lead({"name": "Mover"})
    moved = crm_service.move_lead(lead["id"], "contacted")
    assert moved["pipeline_stage"] == "contacted"


def test_move_lead_invalid_stage():
    lead = crm_service.create_lead({"name": "Invalid"})
    result = crm_service.move_lead(lead["id"], "nonexistent_stage")
    assert result is None


def test_pipeline_summary():
    crm_service.create_lead({"name": "A", "deal_value": 1000})
    crm_service.create_lead({"name": "B", "deal_value": 2000, "pipeline_stage": "trial"})
    summary = crm_service.get_pipeline_summary()
    assert summary["total_leads"] == 2
    assert summary["total_pipeline_value"] == 3000
    assert summary["stages"]["cold"]["count"] == 1
    assert summary["stages"]["trial"]["count"] == 1


def test_get_followups_due():
    crm_service.create_lead({"name": "Due Soon", "next_followup": "2020-01-01"})
    due = crm_service.get_followups_due(days=999999)
    assert len(due) >= 1
