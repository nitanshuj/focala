from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class MoodLogCreate(BaseModel):
    energy_level: int = Field(..., ge=1, le=5)
    mood: Optional[str] = None
    note: Optional[str] = None

class MoodLogResponse(MoodLogCreate):
    id: str
    user_id: str
    logged_at: datetime

class EnergyTrendSummary(BaseModel):
    average_energy: float
    entries_count: int
    recent_logs: List[MoodLogResponse]
