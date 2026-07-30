from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.api.router import api_router
from app.scheduler.daily_planner import scheduler
from app.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    # M5 Fix: validate required secrets at startup — fail fast rather than run insecurely
    if not settings.DEBUG and not settings.JWT_SECRET:
        raise RuntimeError(
            "JWT_SECRET environment variable is required in production. "
            "Set it in your Render dashboard and redeploy."
        )

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
    title="FoCala API — ADHD Planner Backend",
    version="1.0.0",
    description="FastAPI backend for FoCala ADHD planner PWA",
    lifespan=lifespan
)

# H1 Fix: lock CORS to the configured frontend origin(s) only.
# Set ALLOWED_ORIGINS in your environment, e.g.:
#   ALLOWED_ORIGINS=https://focala.netlify.app,https://www.focala.app
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

app.include_router(api_router, prefix="/api")

@app.get("/", tags=["Health"])
async def root():
    return {
        "name": "FoCala API",
        "status": "online",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy"}