from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from datetime import datetime

from app.dependencies import get_current_user
from app.models.task import BrainDumpCreate, BrainDumpResponse
from app.services.supabase_client import supabase
from app.services.gemini_client import triage_brain_dump_with_gemini

router = APIRouter(prefix="/brain-dumps", tags=["Brain Dump"])

@router.get("", response_model=List[BrainDumpResponse])
async def get_brain_dumps(user_id: str = Depends(get_current_user)):
    try:
        res = supabase.table("brain_dumps").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        return res.data or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch brain dumps: {str(e)}")

@router.post("", response_model=BrainDumpResponse, status_code=status.HTTP_201_CREATED)
async def create_brain_dump(
    payload: BrainDumpCreate,
    user_id: str = Depends(get_current_user)
):
    try:
        data = {
            "user_id": user_id,
            "content": payload.content,
            "triaged": False,
            "created_at": datetime.utcnow().isoformat()
        }
        res = supabase.table("brain_dumps").insert(data).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]
        raise HTTPException(status_code=400, detail="Failed to save brain dump")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create brain dump: {str(e)}")

@router.post("/{dump_id}/triage")
async def triage_brain_dump(
    dump_id: str,
    user_id: str = Depends(get_current_user)
):
    try:
        res = supabase.table("brain_dumps").select("*").eq("id", dump_id).eq("user_id", user_id).execute()
        if not res.data or len(res.data) == 0:
            raise HTTPException(status_code=404, detail="Brain dump entry not found")

        entry = res.data[0]
        extracted_tasks = await triage_brain_dump_with_gemini(entry.get("content", ""))

        created_tasks = []
        for task_info in extracted_tasks:
            new_task = {
                "user_id": user_id,
                "title": task_info.get("title", "Brain Dump Task"),
                "description": task_info.get("description", entry.get("content")),
                "priority": task_info.get("priority", "medium"),
                "energy_level": task_info.get("energy_level", "medium"),
                "estimated_minutes": task_info.get("estimated_minutes", 30),
                "status": "pending",
                "ai_generated": True,
                "created_at": datetime.utcnow().isoformat()
            }
            task_res = supabase.table("tasks").insert(new_task).execute()
            if task_res.data:
                created_tasks.append(task_res.data[0])

        # Mark brain dump entry as triaged
        supabase.table("brain_dumps").update({"triaged": True}).eq("id", dump_id).execute()

        return {
            "message": "Brain dump successfully triaged into tasks",
            "created_tasks_count": len(created_tasks),
            "tasks": created_tasks
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to triage brain dump: {str(e)}")
