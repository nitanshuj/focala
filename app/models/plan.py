from pydantic import BaseModel
from typing import List, Optional
from datetime import date, datetime

class ScheduleBlock(BaseModel):
    time_block: str  # "09:00-09:25"
    task_title: str
    task_id: Optional[str] = None
    micro_step: Optional[str] = None
    energy_required: str = "medium"  # low, medium, high
    type: str = "focus"  # focus, break, transition, routine, flex

class DailyPlanOutput(BaseModel):
    schedule: List[ScheduleBlock]
    parked_tasks: List[str] = []
    daily_focus: str
    encouragement: str

class GeneratePlanRequest(BaseModel):
    plan_date: Optional[date] = None
    available_hours: Optional[str] = "09:00-21:00"

class DailyPlanResponse(BaseModel):
    id: str
    user_id: str
    plan_date: date
    schedule: DailyPlanOutput
    created_at: datetime

class RebalancePlanRequest(BaseModel):
    current_time: str  # "14:30"
    completed_task_ids: List[str] = []
    energy_level: str = "medium"
