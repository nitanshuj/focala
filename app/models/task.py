from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    priority: Optional[str] = "medium"  # low, medium, high, urgent
    energy_level: Optional[str] = "medium"  # low, medium, high
    estimated_minutes: Optional[int] = 30
    actual_minutes: Optional[int] = None
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    parent_task_id: Optional[str] = None
    is_micro_step: bool = False

class TaskCreate(TaskBase):
    pass

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None  # pending, in_progress, done, parked
    priority: Optional[str] = None
    energy_level: Optional[str] = None
    estimated_minutes: Optional[int] = None
    actual_minutes: Optional[int] = None
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None

class TaskResponse(TaskBase):
    id: str
    user_id: str
    status: str = "pending"
    ai_generated: bool = False
    completed_at: Optional[datetime] = None
    rolled_over_count: int = 0
    created_at: datetime
    micro_steps: Optional[List["TaskResponse"]] = None

    class Config:
        from_attributes = True

class MicroStepItem(BaseModel):
    title: str
    estimated_minutes: int = 15
    energy_level: str = "low"

class TaskBreakdownResponse(BaseModel):
    task_id: str
    original_title: str
    micro_steps: List[MicroStepItem]

class TaskSummaryResponse(BaseModel):
    completed_today_count: int
    micro_steps_completed_today: int
    total_focus_minutes_today: int
    streak_days: int
    completed_tasks: List[TaskResponse]

class BrainDumpCreate(BaseModel):
    content: str

class BrainDumpResponse(BaseModel):
    id: str
    user_id: str
    content: str
    triaged: bool = False
    converted_task_id: Optional[str] = None
    created_at: datetime

