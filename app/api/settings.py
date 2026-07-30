from fastapi import APIRouter, Depends, HTTPException, status
from app.dependencies import get_current_user
from app.models.settings import UserSettingsResponse, UserSettingsUpdate
from app.services.supabase_client import supabase

router = APIRouter(prefix="/settings", tags=["User Settings"])

@router.get("", response_model=UserSettingsResponse)
async def get_settings(user_id: str = Depends(get_current_user)):
    try:
        res = supabase.table("profiles").select("*").eq("id", user_id).execute()
        if res.data and len(res.data) > 0:
            profile = res.data[0]
            return UserSettingsResponse(
                display_name=profile.get("display_name", "FoCala User"),
                email=profile.get("email", ""),
                reminders_enabled=profile.get("reminders_enabled", True),
                streak_alerts_enabled=profile.get("streak_alerts_enabled", True),
                transition_warnings_enabled=profile.get("transition_warnings_enabled", True),
                energy_pattern=profile.get("energy_pattern", "flexible"),
                ai_planning_enabled=profile.get("ai_planning_enabled", True),
                planning_time=profile.get("planning_time", "08:00"),
                theme=profile.get("theme", "system")
            )
        return UserSettingsResponse()
    except Exception as e:
        # Fallback response if settings columns or profile missing
        return UserSettingsResponse()

@router.patch("", response_model=UserSettingsResponse)
async def update_settings(
    payload: UserSettingsUpdate,
    user_id: str = Depends(get_current_user)
):
    try:
        update_data = payload.model_dump(exclude_unset=True)
        if update_data:
            supabase.table("profiles").upsert({"id": user_id, **update_data}).execute()
        return await get_settings(user_id=user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update settings: {str(e)}")

@router.get("/export")
async def export_user_data(user_id: str = Depends(get_current_user)):
    """
    Exports all of the authenticated user's data.
    M6 Fix: each table is capped at 1000 rows to prevent unbounded memory usage.
    For large datasets, implement cursor-based pagination.
    """
    try:
        PAGE = 1000  # safety cap per table
        tasks = supabase.table("tasks").select("*").eq("user_id", user_id).limit(PAGE).execute().data or []
        routines = supabase.table("routines").select("*").eq("user_id", user_id).limit(PAGE).execute().data or []
        moods = supabase.table("mood_logs").select("*").eq("user_id", user_id).limit(PAGE).execute().data or []
        brain_dumps = supabase.table("brain_dumps").select("*").eq("user_id", user_id).limit(PAGE).execute().data or []
        plans = supabase.table("daily_plans").select("*").eq("user_id", user_id).limit(PAGE).execute().data or []
        return {
            "tasks": tasks,
            "routines": routines,
            "mood_logs": moods,
            "brain_dumps": brain_dumps,
            "daily_plans": plans
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export data: {str(e)}")

@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(user_id: str = Depends(get_current_user)):
    try:
        tables = ["tasks", "routines", "mood_logs", "brain_dumps", "daily_plans", "profiles"]
        for t in tables:
            supabase.table(t).delete().eq("user_id" if t != "profiles" else "id", user_id).execute()
        return None
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete account: {str(e)}")
