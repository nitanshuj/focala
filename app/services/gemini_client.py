import google.generativeai as genai
import json
import logging
from datetime import date
from typing import Dict, Any, List
from app.config import settings

logger = logging.getLogger(__name__)

if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)

def get_model_name() -> str:
    return settings.GEMINI_MODEL_NAME

def get_backup_model_name() -> str:
    return settings.GEMINI_BACKUP_MODEL_NAME

def generate_content_with_fallback(prompt: str) -> str:
    """
    Attempts to generate content using primary model GEMINI_MODEL_NAME.
    If it fails, falls back to GEMINI_BACKUP_MODEL_NAME.
    """
    models_to_try = [
        settings.GEMINI_MODEL_NAME,
        settings.GEMINI_BACKUP_MODEL_NAME
    ]
    
    # Remove empty or duplicate model names
    seen = set()
    models = []
    for m in models_to_try:
        if m and m not in seen:
            seen.add(m)
            models.append(m)

    last_error = None
    for model_name in models:
        try:
            logger.info(f"Generating content with Gemini model: {model_name}")
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.warning(f"Gemini request failed using model '{model_name}': {e}. Retrying with fallback model...")
            last_error = e

    raise last_error or RuntimeError("All configured Gemini models failed.")

DAILY_PLANNER_PROMPT = """
You are an ADHD-friendly daily planner assistant. Given the user's tasks, routines, and available time windows, create an optimized daily schedule.

ADHD PRINCIPLES TO FOLLOW STRICTLY:
1. Never schedule more than 3 high-priority focus tasks per day.
2. Break large tasks into a clear micro-step (the absolute first physical action).
3. Place high-energy tasks during peak energy windows.
4. Include 15-minute transition buffers between focus blocks.
5. Add 2 "flex blocks" (30 minutes each) for overflow or meltdown recovery.
6. If tasks exceed available time, park the lowest-priority ones (do not overload).
7. Keep tone encouraging, supportive, and zero-guilt.

Return strictly valid JSON with this structure:
{
  "schedule": [
    {
      "time_block": "09:00-09:25",
      "task_title": "Clean desk",
      "task_id": "optional-id",
      "micro_step": "First action: Put pens in holder",
      "energy_required": "low",
      "type": "routine"
    }
  ],
  "parked_tasks": ["task_id_1"],
  "daily_focus": "One sentence main priority today",
  "encouragement": "Short encouraging note for ADHD focus"
}
"""

BREAKDOWN_PROMPT = """
You are an ADHD executive dysfunction helper. The user feels overwhelmed by a task.
Break down the task into 3 to 5 low-friction micro-steps. The first step MUST be a tiny, frictionless physical action (e.g. "Open laptop", "Pick up pen").

Task: {task_title}
Description: {task_description}

Return strictly valid JSON:
{
  "micro_steps": [
    {
      "title": "First micro step...",
      "estimated_minutes": 10,
      "energy_level": "low"
    }
  ]
}
"""

TRIAGE_PROMPT = """
You are an ADHD brain dump assistant. Parse the raw brain dump text and extract distinct tasks with reasonable estimates.

Text: {brain_dump_content}

Return strictly valid JSON:
{
  "extracted_tasks": [
    {
      "title": "Task title",
      "description": "Optional details",
      "priority": "low" | "medium" | "high",
      "energy_level": "low" | "medium" | "high",
      "estimated_minutes": 20
    }
  ]
}
"""


async def generate_gemini_daily_plan(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calls Gemini API to generate ADHD daily schedule with fallback model support.
    """
    if not settings.GEMINI_API_KEY:
        return {
            "schedule": [
                {
                    "time_block": "09:00-09:30",
                    "task_title": "Morning Routine & Setup",
                    "task_id": None,
                    "micro_step": "Drink water & open planner",
                    "energy_required": "low",
                    "type": "routine"
                },
                {
                    "time_block": "09:45-10:45",
                    "task_title": context.get("tasks", [{}])[0].get("title", "Focus Task 1") if context.get("tasks") else "Main Focus Task",
                    "task_id": context.get("tasks", [{}])[0].get("id") if context.get("tasks") else None,
                    "micro_step": "Open document and write first bullet point",
                    "energy_required": "high",
                    "type": "focus"
                },
                {
                    "time_block": "11:00-11:30",
                    "task_title": "Buffer & Recharge Block",
                    "task_id": None,
                    "micro_step": "Step away from screen",
                    "energy_required": "low",
                    "type": "flex"
                }
            ],
            "parked_tasks": [],
            "daily_focus": "Focus on high-value tasks with ample rest breaks.",
            "encouragement": "You've got this! Take it one micro-step at a time."
        }

    try:
        prompt = f"{DAILY_PLANNER_PROMPT}\n\nUser Context:\n{json.dumps(context, default=str)}"
        text = generate_content_with_fallback(prompt)
        if text.startswith("```json"):
            text = text[7:].rstrip("` \n")
        elif text.startswith("```"):
            text = text[3:].rstrip("` \n")
        return json.loads(text)
    except Exception as e:
        logger.error(f"Gemini Daily Plan generation error: {e}")
        raise RuntimeError(f"Failed to generate daily plan with Gemini: {str(e)}")


async def breakdown_task_with_gemini(task_title: str, task_description: str = "") -> List[Dict[str, Any]]:
    """
    Breaks down a task into micro-steps using Gemini with fallback model support.
    """
    if not settings.GEMINI_API_KEY:
        return [
            {"title": f"Open workspace for '{task_title}'", "estimated_minutes": 5, "energy_level": "low"},
            {"title": "Review instructions & initial draft", "estimated_minutes": 15, "energy_level": "medium"},
            {"title": "Complete main section", "estimated_minutes": 20, "energy_level": "high"}
        ]

    try:
        prompt = BREAKDOWN_PROMPT.format(task_title=task_title, task_description=task_description or "None")
        text = generate_content_with_fallback(prompt)
        if text.startswith("```json"):
            text = text[7:].rstrip("` \n")
        elif text.startswith("```"):
            text = text[3:].rstrip("` \n")
        data = json.loads(text)
        return data.get("micro_steps", [])
    except Exception as e:
        logger.error(f"Gemini task breakdown error: {e}")
        return [
            {"title": f"Start {task_title}", "estimated_minutes": 15, "energy_level": "medium"}
        ]


async def triage_brain_dump_with_gemini(content: str) -> List[Dict[str, Any]]:
    """
    Triages raw brain dump into tasks using Gemini with fallback model support.
    """
    if not settings.GEMINI_API_KEY:
        return [
            {
                "title": content[:50] + ("..." if len(content) > 50 else ""),
                "description": content,
                "priority": "medium",
                "energy_level": "medium",
                "estimated_minutes": 30
            }
        ]

    try:
        prompt = TRIAGE_PROMPT.format(brain_dump_content=content)
        text = generate_content_with_fallback(prompt)
        if text.startswith("```json"):
            text = text[7:].rstrip("` \n")
        elif text.startswith("```"):
            text = text[3:].rstrip("` \n")
        data = json.loads(text)
        return data.get("extracted_tasks", [])
    except Exception as e:
        logger.error(f"Gemini triage error: {e}")
        return [{
            "title": content[:60],
            "description": content,
            "priority": "medium",
            "energy_level": "medium",
            "estimated_minutes": 30
        }]
