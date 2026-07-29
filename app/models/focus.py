from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class FocusSessionLog(BaseModel):
    duration_minutes: int = 25
    task_id: Optional[str] = None
    ambient_mode: Optional[str] = "white_noise"  # soundscape, body_double, silent

class FocusSessionResponse(BaseModel):
    status: str = "completed"
    duration_minutes: int
    reward_earned: str = "🌟 Focus Win logged!"
    ambient_mode: str
    logged_at: datetime
