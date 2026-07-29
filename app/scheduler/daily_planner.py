import logging
from datetime import date
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.services.supabase_client import supabase
from app.services.gemini_client import generate_gemini_daily_plan
from app.services.push_service import send_push_notification

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job(CronTrigger(hour=7, minute=0))
async def daily_planning_job():
    """
    Automated 7 AM daily plan generation for all users with gemini_enabled = True.
    """
    logger.info("Executing daily planning scheduled job...")
    try:
        res = supabase.table("profiles").select("id").eq("gemini_enabled", True).execute()
        users = res.data or []
        for user in users:
            user_id = user.get("id")
            if not user_id:
                continue
            try:
                tasks_res = supabase.table("tasks").select("*").eq("user_id", user_id).eq("status", "pending").execute()
                routines_res = supabase.table("routines").select("*").eq("user_id", user_id).eq("active", True).execute()

                context = {
                    "tasks": tasks_res.data or [],
                    "routines": routines_res.data or [],
                    "date": str(date.today())
                }

                plan = await generate_gemini_daily_plan(context)
                supabase.table("daily_plans").upsert({
                    "user_id": user_id,
                    "plan_date": str(date.today()),
                    "schedule": plan,
                    "raw_gemini_response": str(plan)
                }, on_conflict="user_id,plan_date").execute()

                await send_push_notification(
                    user_id=user_id,
                    title="📅 Good morning! Your schedule is ready",
                    body=plan.get("daily_focus", "Tap to view today's tasks & routines."),
                    url="/today"
                )
            except Exception as ex:
                logger.error(f"Daily planning failed for user {user_id}: {ex}")
    except Exception as e:
        logger.error(f"Error executing scheduled daily planning job: {e}")

@scheduler.scheduled_job(CronTrigger(minute="*/5"))
async def transition_reminders():
    """
    Checks upcoming focus time blocks every 5 minutes and sends push warnings.
    """
    # Placeholder for checking scheduled time blocks and sending 5-min warnings
    pass

@scheduler.scheduled_job(CronTrigger(hour=20, minute=0))
async def evening_checkin():
    """
    8 PM gentle reminder to reflect on daily progress & log mood.
    """
    try:
        res = supabase.table("profiles").select("id").execute()
        users = res.data or []
        for user in users:
            await send_push_notification(
                user_id=user["id"],
                title="🌙 Evening Reflection",
                body="How was your energy today? Take 10 seconds for a quick check-in.",
                url="/mood"
            )
    except Exception as e:
        logger.error(f"Evening checkin notification error: {e}")
