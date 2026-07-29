from fastapi import APIRouter, Depends, HTTPException
from app.dependencies import get_current_user
from app.models.calendar import CalendarSyncResponse
from app.services.calendar_client import fetch_user_google_calendar_events

router = APIRouter(prefix="/calendar", tags=["Calendar"])

@router.get("/events", response_model=CalendarSyncResponse)
async def get_calendar_events(user_id: str = Depends(get_current_user)):
    try:
        events = await fetch_user_google_calendar_events(user_id)
        return {
            "synced_events_count": len(events),
            "events": events
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch calendar events: {str(e)}")
