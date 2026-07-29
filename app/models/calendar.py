from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class CalendarEvent(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    is_all_day: bool = False

class CalendarSyncResponse(BaseModel):
    synced_events_count: int
    events: List[CalendarEvent]
