from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, date

class RoutineStep(BaseModel):
    label: str
    icon: Optional[str] = "check"
    est_minutes: int = 10

class RoutineBase(BaseModel):
    name: str
    trigger_time: Optional[str] = None  # e.g., "08:00"
    active: bool = True
    steps: List[RoutineStep] = []

class RoutineCreate(RoutineBase):
    pass

class RoutineUpdate(BaseModel):
    name: Optional[str] = None
    trigger_time: Optional[str] = None
    active: Optional[bool] = None
    steps: Optional[List[RoutineStep]] = None

class RoutineResponse(RoutineBase):
    id: str
    user_id: str
    created_at: datetime

class RoutineCompletionRequest(BaseModel):
    completed_steps: List[str]
    completed_at: Optional[date] = None

class RoutineCompletionResponse(BaseModel):
    id: str
    user_id: str
    routine_id: str
    completed_steps: List[str]
    completed_at: date
