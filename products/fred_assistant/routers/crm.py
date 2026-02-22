"""CRM router — Leads, pipeline, outreach, followups."""

from fastapi import APIRouter, HTTPException, Query

from products.fred_assistant.models import LeadCreate, LeadUpdate, OutreachEntry, FollowupRequest
from products.fred_assistant.services import crm_service

router = APIRouter(prefix="/crm", tags=["crm"])


@router.get("/leads")
def list_leads(stage: str = Query(None), source: str = Query(None)):
    return crm_service.list_leads(stage=stage, source=source)


@router.get("/leads/{lead_id}")
def get_lead(lead_id: str):
    lead = crm_service.get_lead(lead_id)
    if not lead:
        raise HTTPException(404, "Lead not found")
    return lead


@router.post("/leads")
def create_lead(data: LeadCreate):
    return crm_service.create_lead(data.model_dump())


@router.patch("/leads/{lead_id}")
def update_lead(lead_id: str, data: LeadUpdate):
    lead = crm_service.update_lead(lead_id, data.model_dump(exclude_unset=True))
    if not lead:
        raise HTTPException(404, "Lead not found")
    return lead


@router.delete("/leads/{lead_id}", status_code=204)
def delete_lead(lead_id: str):
    crm_service.delete_lead(lead_id)


@router.post("/leads/{lead_id}/outreach")
def log_outreach(lead_id: str, data: OutreachEntry):
    return crm_service.log_outreach(
        lead_id=lead_id,
        outreach_type=data.outreach_type,
        content=data.content,
        result=data.result,
    )


@router.get("/leads/{lead_id}/outreach")
def get_outreach(lead_id: str):
    return crm_service.get_outreach_history(lead_id)


@router.post("/leads/{lead_id}/followup")
def schedule_followup(lead_id: str, data: FollowupRequest):
    result = crm_service.schedule_followup(lead_id, data.date, data.notes)
    if not result:
        raise HTTPException(404, "Lead not found")
    return result


@router.get("/pipeline")
def pipeline_summary():
    return crm_service.get_pipeline_summary()


@router.get("/followups")
def followups_due(days: int = Query(3, ge=1, le=30)):
    return crm_service.get_followups_due(days)
