from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from datetime import datetime
import uuid

from app.dependencies import get_current_user
from app.models.task import TaskCreate, TaskUpdate, TaskResponse, TaskBreakdownResponse, TaskSummaryResponse
from app.services.supabase_client import supabase
from app.services.gemini_client import breakdown_task_with_gemini

router = APIRouter(prefix="/tasks", tags=["Tasks"])

@router.get("", response_model=List[TaskResponse])
async def get_tasks(
    status_filter: Optional[str] = Query(None, alias="status"),
    user_id: str = Depends(get_current_user)
):
    try:
        query = supabase.table("tasks").select("*").eq("user_id", user_id)
        if status_filter:
            query = query.eq("status", status_filter)
        res = query.order("created_at", desc=True).execute()
        return res.data or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch tasks: {str(e)}")

@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task: TaskCreate,
    user_id: str = Depends(get_current_user)
):
    try:
        task_data = task.model_dump()
        task_data["user_id"] = user_id
        task_data["created_at"] = datetime.utcnow().isoformat()
        res = supabase.table("tasks").insert(task_data).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]
        raise HTTPException(status_code=400, detail="Failed to create task")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create task: {str(e)}")

@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    update_data: TaskUpdate,
    user_id: str = Depends(get_current_user)
):
    try:
        data = update_data.model_dump(exclude_unset=True)
        if data.get("status") == "done":
            data["completed_at"] = datetime.utcnow().isoformat()
        res = supabase.table("tasks").update(data).eq("id", task_id).eq("user_id", user_id).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]
        raise HTTPException(status_code=404, detail="Task not found or access denied")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update task: {str(e)}")

@router.delete("/completed", status_code=status.HTTP_204_NO_CONTENT)
async def clear_completed_tasks(
    user_id: str = Depends(get_current_user)
):
    try:
        supabase.table("tasks").delete().eq("user_id", user_id).eq("status", "done").execute()
        return None
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear completed tasks: {str(e)}")

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: str,
    user_id: str = Depends(get_current_user)
):
    try:
        supabase.table("tasks").delete().eq("id", task_id).eq("user_id", user_id).execute()
        return None
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete task: {str(e)}")

@router.post("/breakdown")
async def breakdown_task_standalone(
    payload: dict,
    user_id: str = Depends(get_current_user)
):
    try:
        title = payload.get("title", "")
        description = payload.get("description", "")
        micro_steps_data = await breakdown_task_with_gemini(
            task_title=title,
            task_description=description
        )
        steps = [step.get("title", "") for step in micro_steps_data if step.get("title")]
        return {"steps": steps}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to breakdown task: {str(e)}")

@router.post("/{task_id}/breakdown", response_model=TaskBreakdownResponse)
async def breakdown_task(
    task_id: str,
    user_id: str = Depends(get_current_user)
):
    try:
        res = supabase.table("tasks").select("*").eq("id", task_id).eq("user_id", user_id).execute()
        if not res.data or len(res.data) == 0:
            raise HTTPException(status_code=404, detail="Task not found")

        task = res.data[0]
        micro_steps_data = await breakdown_task_with_gemini(
            task_title=task.get("title", ""),
            task_description=task.get("description", "")
        )

        created_micro_steps = []
        for step in micro_steps_data:
            child_task = {
                "user_id": user_id,
                "title": step.get("title", "Micro step"),
                "estimated_minutes": step.get("estimated_minutes", 15),
                "energy_level": step.get("energy_level", "low"),
                "parent_task_id": task_id,
                "is_micro_step": True,
                "ai_generated": True,
                "status": "pending",
                "created_at": datetime.utcnow().isoformat()
            }
            sub_res = supabase.table("tasks").insert(child_task).execute()
            if sub_res.data:
                created_micro_steps.append(sub_res.data[0])

        return {
            "task_id": task_id,
            "original_title": task.get("title", ""),
            "micro_steps": [
                {
                    "title": step.get("title", ""),
                    "estimated_minutes": step.get("estimated_minutes", 15),
                    "energy_level": step.get("energy_level", "low")
                }
                for step in micro_steps_data
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to breakdown task: {str(e)}")

@router.post("/rollover")
async def rollover_unfinished_tasks(
    user_id: str = Depends(get_current_user)
):
    """
    Auto-rollover pending tasks created prior to today, incrementing rolled_over_count.
    Prevents tasks from falling through the cracks (ADHD working memory support).
    """
    try:
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        res = supabase.table("tasks").select("*").eq("user_id", user_id).eq("status", "pending").lt("created_at", today_start).execute()
        past_tasks = res.data or []

        rolled_over = []
        for t in past_tasks:
            new_count = t.get("rolled_over_count", 0) + 1
            upd = supabase.table("tasks").update({"rolled_over_count": new_count}).eq("id", t["id"]).execute()
            if upd.data:
                rolled_over.append(upd.data[0])

        return {
            "message": f"Rolled over {len(rolled_over)} unfinished task(s)",
            "rolled_over_count": len(rolled_over),
            "tasks": rolled_over
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to rollover tasks: {str(e)}")

@router.get("/summary/today", response_model=TaskSummaryResponse)
async def get_today_task_summary(
    user_id: str = Depends(get_current_user)
):
    """
    Returns reverse to-do list data & dopamine progress summary for today.
    """
    try:
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        res = supabase.table("tasks").select("*").eq("user_id", user_id).eq("status", "done").gte("completed_at", today_start).execute()
        completed = res.data or []

        micro_steps_completed = sum(1 for t in completed if t.get("is_micro_step"))
        total_focus_minutes = sum(t.get("actual_minutes") or t.get("estimated_minutes") or 15 for t in completed)

        return {
            "completed_today_count": len(completed),
            "micro_steps_completed_today": micro_steps_completed,
            "total_focus_minutes_today": total_focus_minutes,
            "streak_days": 1 if len(completed) > 0 else 0,
            "completed_tasks": completed
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch today task summary: {str(e)}")

