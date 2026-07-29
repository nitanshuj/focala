from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from datetime import datetime

from app.dependencies import get_current_user
from app.models.mood import MoodLogCreate, MoodLogResponse, EnergyTrendSummary
from app.services.supabase_client import supabase

router = APIRouter(prefix="/mood", tags=["Mood & Energy"])

@router.post("", response_model=MoodLogResponse, status_code=status.HTTP_201_CREATED)
async def log_mood(
    payload: MoodLogCreate,
    user_id: str = Depends(get_current_user)
):
    try:
        record = {
            "user_id": user_id,
            "energy_level": payload.energy_level,
            "mood": payload.mood,
            "note": payload.note,
            "logged_at": datetime.utcnow().isoformat()
        }
        res = supabase.table("mood_logs").insert(record).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]
        raise HTTPException(status_code=400, detail="Failed to log mood")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to log mood: {str(e)}")

@router.get("/trends", response_model=EnergyTrendSummary)
async def get_mood_trends(user_id: str = Depends(get_current_user)):
    try:
        res = supabase.table("mood_logs").select("*").eq("user_id", user_id).order("logged_at", desc=True).limit(30).execute()
        logs = res.data or []
        
        if not logs:
            return {
                "average_energy": 3.0,
                "entries_count": 0,
                "recent_logs": []
            }
        
        avg = sum(item.get("energy_level", 3) for item in logs) / len(logs)
        return {
            "average_energy": round(avg, 2),
            "entries_count": len(logs),
            "recent_logs": logs
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch mood trends: {str(e)}")
