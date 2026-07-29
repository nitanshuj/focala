from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.api.router import api_router
from app.scheduler.daily_planner import scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start APScheduler background scheduler
    try:
        scheduler.start()
    except Exception as e:
        print(f"Scheduler start error: {e}")
    yield
    # Shutdown: Shutdown APScheduler cleanly
    try:
        scheduler.shutdown(wait=False)
    except Exception as e:
        print(f"Scheduler shutdown error: {e}")

app = FastAPI(
    title="FocusFlow API — ADHD Planner Backend",
    version="1.0.0",
    description="FastAPI backend for FocusFlow ADHD planner PWA",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configurable for PWA domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")

@app.get("/", tags=["Health"])
async def root():
    return {
        "name": "FocusFlow API",
        "status": "online",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy"}