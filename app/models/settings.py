from pydantic import BaseModel
from typing import Optional

class UserSettingsResponse(BaseModel):
    display_name: Optional[str] = "FoCala User"
    email: Optional[str] = ""
    reminders_enabled: bool = True
    streak_alerts_enabled: bool = True
    transition_warnings_enabled: bool = True
    energy_pattern: str = "flexible"
    ai_planning_enabled: bool = True
    planning_time: str = "08:00"
    theme: str = "system"

class UserSettingsUpdate(BaseModel):
    display_name: Optional[str] = None
    email: Optional[str] = None
    reminders_enabled: Optional[bool] = None
    streak_alerts_enabled: Optional[bool] = None
    transition_warnings_enabled: Optional[bool] = None
    energy_pattern: Optional[str] = None
    ai_planning_enabled: Optional[bool] = None
    planning_time: Optional[str] = None
    theme: Optional[str] = None
