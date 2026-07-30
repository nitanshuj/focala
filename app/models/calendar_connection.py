from pydantic import BaseModel
from typing import Optional, List

class CalendarConnectionStatus(BaseModel):
    connected: bool
    google_email: Optional[str] = None
    connected_at: Optional[str] = None

class CreateCalendarEventRequest(BaseModel):
    summary: str
    description: Optional[str] = None
    start_time: str
    end_time: str
    location: Optional[str] = None

class UpdateCalendarEventRequest(BaseModel):
    summary: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    location: Optional[str] = None

class GoogleCalendarEvent(BaseModel):
    id: str
    summary: str
    description: Optional[str] = None
    start_time: str
    end_time: str
    location: Optional[str] = None

class CalendarSyncResponse(BaseModel):
    synced_events_count: int
    events: List[dict]
