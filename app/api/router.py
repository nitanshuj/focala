from fastapi import APIRouter
from app.api import tasks, brain_dump, routines, planning, calendar, push

api_router = APIRouter()
api_router.include_router(tasks.router)
api_router.include_router(brain_dump.router)
api_router.include_router(routines.router)
api_router.include_router(planning.router)
api_router.include_router(calendar.router)
api_router.include_router(push.router)