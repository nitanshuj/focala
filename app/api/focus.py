from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime
from typing import List, Dict, Any

from app.dependencies import get_current_user
from app.models.focus import FocusSessionLog, FocusSessionResponse
from app.services.supabase_client import supabase

router = APIRouter(prefix="/focus", tags=["Focus & Body Doubling"])

@router.post("/session", response_model=FocusSessionResponse, status_code=status.HTTP_201_CREATED)
async def log_focus_session(
    payload: FocusSessionLog,
    user_id: str = Depends(get_current_user)
):
    """
    Logs a completed focus / body-doubling session and awards immediate micro-reward.
    """
    try:
        now = datetime.utcnow()
        record = {
            "user_id": user_id,
            "duration_minutes": payload.duration_minutes,
            "task_id": payload.task_id,
            "ambient_mode": payload.ambient_mode or "white_noise",
            "logged_at": now.isoformat()
        }
        res = supabase.table("focus_sessions").insert(record).execute()

        # If a task was linked, update its actual_minutes
        if payload.task_id:
            task_res = supabase.table("tasks").select("actual_minutes").eq("id", payload.task_id).execute()
            if task_res.data and len(task_res.data) > 0:
                current_min = task_res.data[0].get("actual_minutes") or 0
                supabase.table("tasks").update({"actual_minutes": current_min + payload.duration_minutes}).eq("id", payload.task_id).execute()

        return {
            "status": "completed",
            "duration_minutes": payload.duration_minutes,
            "reward_earned": f"🎉 {payload.duration_minutes}-min Focus session completed!",
            "ambient_mode": payload.ambient_mode or "white_noise",
            "logged_at": now
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to log focus session: {str(e)}")

@router.get("/rooms")
async def get_ambient_body_doubling_rooms():
    """
    Returns virtual body doubling rooms & ambient soundscapes.
    """
    return {
        "active_rooms": [
            {"id": "room-1", "name": "Quiet Library", "active_users": 14, "ambient": "soft_rain"},
            {"id": "room-2", "name": "Coffee Shop Buzz", "active_users": 8, "ambient": "cafe"},
            {"id": "room-3", "name": "Deep Space Focus", "active_users": 22, "ambient": "binaural_beats"}
        ]
    }
