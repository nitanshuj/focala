from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from datetime import datetime, date

from app.dependencies import get_current_user
from app.models.routine import (
    RoutineCreate, RoutineUpdate, RoutineResponse,
    RoutineCompletionRequest, RoutineCompletionResponse
)
from app.services.supabase_client import supabase

router = APIRouter(prefix="/routines", tags=["Routines"])

@router.get("", response_model=List[RoutineResponse])
async def get_routines(user_id: str = Depends(get_current_user)):
    try:
        res = supabase.table("routines").select("*").eq("user_id", user_id).execute()
        return res.data or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch routines: {str(e)}")

@router.post("", response_model=RoutineResponse, status_code=status.HTTP_201_CREATED)
async def create_routine(
    routine: RoutineCreate,
    user_id: str = Depends(get_current_user)
):
    try:
        data = routine.model_dump()
        data["user_id"] = user_id
        data["created_at"] = datetime.utcnow().isoformat()
        res = supabase.table("routines").insert(data).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]
        raise HTTPException(status_code=400, detail="Failed to create routine")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create routine: {str(e)}")

@router.patch("/{routine_id}", response_model=RoutineResponse)
async def update_routine(
    routine_id: str,
    update_data: RoutineUpdate,
    user_id: str = Depends(get_current_user)
):
    try:
        data = update_data.model_dump(exclude_unset=True)
        res = supabase.table("routines").update(data).eq("id", routine_id).eq("user_id", user_id).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]
        raise HTTPException(status_code=404, detail="Routine not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update routine: {str(e)}")

@router.post("/{routine_id}/complete", response_model=RoutineCompletionResponse)
async def complete_routine_steps(
    routine_id: str,
    payload: RoutineCompletionRequest,
    user_id: str = Depends(get_current_user)
):
    try:
        completed_date = str(payload.completed_at or date.today())
        record = {
            "user_id": user_id,
            "routine_id": routine_id,
            "completed_steps": payload.completed_steps,
            "completed_at": completed_date
        }
        res = supabase.table("routine_completions").upsert(record).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]
        raise HTTPException(status_code=400, detail="Failed to save routine completion")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to complete routine steps: {str(e)}")
