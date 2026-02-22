from fastapi import APIRouter

from products.fred_assistant.models import BriefingOut
from products.fred_assistant.services import assistant

router = APIRouter(prefix="/briefing", tags=["briefing"])


@router.get("/today")
async def get_today_briefing():
    briefing = assistant.get_today_briefing()
    if briefing:
        return briefing
    return {"date": None, "content": "No briefing generated yet. Hit POST to create one."}


@router.post("", response_model=BriefingOut)
async def generate_briefing():
    return await assistant.generate_briefing()
