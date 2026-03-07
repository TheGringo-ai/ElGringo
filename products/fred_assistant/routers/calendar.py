"""Calendar router — events, time blocks, deadlines."""

from fastapi import APIRouter, HTTPException, Query
from products.fred_assistant.models import CalendarEventCreate, CalendarEventUpdate
from products.fred_assistant.services import calendar_service

router = APIRouter(prefix="/calendar", tags=["calendar"])


@router.get("/events")
def list_events(
    start_date: str = Query(None),
    end_date: str = Query(None),
    event_type: str = Query(None),
):
    return calendar_service.list_events(start_date, end_date, event_type)


@router.get("/today")
def today_events():
    return calendar_service.get_today_events()


@router.get("/week")
def week_events():
    return calendar_service.get_week_events()


@router.get("/upcoming")
def upcoming_events(days: int = Query(7, ge=1, le=90)):
    return calendar_service.get_upcoming(days)


@router.get("/events/{event_id}")
def get_event(event_id: str):
    event = calendar_service.get_event(event_id)
    if not event:
        raise HTTPException(404, "Event not found")
    return event


@router.post("/events")
def create_event(data: CalendarEventCreate):
    return calendar_service.create_event(data.model_dump())


@router.patch("/events/{event_id}")
def update_event(event_id: str, data: CalendarEventUpdate):
    event = calendar_service.update_event(event_id, data.model_dump(exclude_unset=True))
    if not event:
        raise HTTPException(404, "Event not found")
    return event


@router.delete("/events/{event_id}", status_code=204)
def delete_event(event_id: str):
    calendar_service.delete_event(event_id)
