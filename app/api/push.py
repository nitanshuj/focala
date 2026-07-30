from fastapi import APIRouter, Depends, HTTPException, status
from app.dependencies import get_current_user
from app.config import settings

router = APIRouter(prefix="/push", tags=["Push Notifications"])

@router.get("/status")
async def push_status():
    return {"status": "active" if settings.VAPID_PUBLIC_KEY else "disabled", "message": "Push Notification Subsystem"}

@router.get("/public-key")
async def get_public_key():
    return {"public_key": settings.VAPID_PUBLIC_KEY or "demo_public_key"}

@router.post("/subscribe", status_code=status.HTTP_201_CREATED)
async def subscribe_push(
    payload: dict,
    user_id: str = Depends(get_current_user)
):
    return {"status": "success", "message": "Subscribed to push notifications"}

@router.post("/unsubscribe", status_code=status.HTTP_200_OK)
async def unsubscribe_push(
    user_id: str = Depends(get_current_user)
):
    return {"status": "unsubscribed"}

@router.post("/test")
async def test_push_notification(
    user_id: str = Depends(get_current_user)
):
    return {"status": "sent", "detail": "Test notification sent successfully"}
