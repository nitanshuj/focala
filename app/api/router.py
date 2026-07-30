from fastapi import APIRouter
from app.api import auth, tasks, brain_dump, routines, planning, calendar, push, mood, focus, settings

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(tasks.router)
api_router.include_router(brain_dump.router)
api_router.include_router(routines.router)
api_router.include_router(planning.router)
api_router.include_router(calendar.router)
api_router.include_router(push.router)
api_router.include_router(mood.router)
api_router.include_router(focus.router)
api_router.include_router(settings.router)