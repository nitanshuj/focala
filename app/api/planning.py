from fastapi import APIRouter, Depends, HTTPException, status
from datetime import date, datetime
from typing import Optional

from app.dependencies import get_current_user
from app.models.plan import GeneratePlanRequest, DailyPlanResponse, RebalancePlanRequest
from app.services.supabase_client import supabase
from app.services.gemini_client import generate_gemini_daily_plan
from app.services.push_service import send_push_notification

router = APIRouter(prefix="/plan", tags=["Daily Planning"])

@router.post("/generate", response_model=DailyPlanResponse)
async def generate_daily_plan_endpoint(
    payload: Optional[GeneratePlanRequest] = None,
    user_id: str = Depends(get_current_user)
):
    try:
        plan_date_val = (payload.plan_date if payload and payload.plan_date else date.today())
        
        # Fetch pending tasks and active routines from Supabase
        tasks_res = supabase.table("tasks").select("*").eq("user_id", user_id).eq("status", "pending").execute()
        routines_res = supabase.table("routines").select("*").eq("user_id", user_id).eq("active", True).execute()
        profile_res = supabase.table("profiles").select("*").eq("id", user_id).execute()

        profile_data = profile_res.data[0] if (profile_res.data and len(profile_res.data) > 0) else {}

        context = {
            "tasks": tasks_res.data or [],
            "routines": routines_res.data or [],
            "energy_pattern": profile_data.get("energy_pattern", "flexible"),
            "available_hours": payload.available_hours if payload else "09:00-21:00",
            "date": str(plan_date_val)
        }

        # Generate daily schedule with Gemini
        ai_output = await generate_gemini_daily_plan(context)

        db_record = {
            "user_id": user_id,
            "plan_date": str(plan_date_val),
            "schedule": ai_output,
            "raw_gemini_response": str(ai_output),
            "created_at": datetime.utcnow().isoformat()
        }

        res = supabase.table("daily_plans").upsert(db_record, on_conflict="user_id,plan_date").execute()
        
        # Send Web Push notification
        await send_push_notification(
            user_id=user_id,
            title="📅 Your AI Daily Schedule is Ready",
            body=ai_output.get("daily_focus", "Tap to view your focus blocks for today."),
            url="/today"
        )

        if res.data and len(res.data) > 0:
            return res.data[0]
        
        return {
            "id": "generated-plan-id",
            "user_id": user_id,
            "plan_date": plan_date_val,
            "schedule": ai_output,
            "created_at": datetime.utcnow()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate daily plan: {str(e)}")

@router.get("/today")
async def get_today_plan(user_id: str = Depends(get_current_user)):
    try:
        today_str = str(date.today())
        res = supabase.table("daily_plans").select("*").eq("user_id", user_id).eq("plan_date", today_str).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]
        return {
            "plan_date": today_str,
            "schedule": None,
            "message": "No plan generated yet for today. Use /api/plan/generate to create one."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch today's plan: {str(e)}")

@router.post("/rebalance")
async def rebalance_plan_endpoint(
    payload: RebalancePlanRequest,
    user_id: str = Depends(get_current_user)
):
    try:
        today_str = str(date.today())
        existing = supabase.table("daily_plans").select("*").eq("user_id", user_id).eq("plan_date", today_str).execute()
        
        tasks_res = supabase.table("tasks").select("*").eq("user_id", user_id).eq("status", "pending").execute()

        context = {
            "tasks": tasks_res.data or [],
            "current_time": payload.current_time,
            "user_energy": payload.energy_level,
            "note": "Mid-day rebalance requested due to schedule drift."
        }

        rebalanced_output = await generate_gemini_daily_plan(context)
        
        db_record = {
            "user_id": user_id,
            "plan_date": today_str,
            "schedule": rebalanced_output,
            "raw_gemini_response": str(rebalanced_output),
            "created_at": datetime.utcnow().isoformat()
        }
        res = supabase.table("daily_plans").upsert(db_record, on_conflict="user_id,plan_date").execute()

        await send_push_notification(
            user_id=user_id,
            title="⚡ Schedule Rebalanced",
            body=rebalanced_output.get("encouragement", "Adjusted for your current energy level."),
            url="/today"
        )

        return res.data[0] if (res.data and len(res.data) > 0) else db_record
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to rebalance plan: {str(e)}")
