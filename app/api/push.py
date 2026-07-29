from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime

from app.dependencies import get_current_user
from app.models.push import PushSubscribeRequest, PushSubscribeResponse, PushTestNotification
from app.services.supabase_client import supabase
from app.services.push_service import send_push_notification

router = APIRouter(prefix="/push", tags=["Push Notifications"])

@router.post("/subscribe", response_model=PushSubscribeResponse, status_code=status.HTTP_201_CREATED)
async def subscribe_push(
    payload: PushSubscribeRequest,
    user_id: str = Depends(get_current_user)
):
    try:
        record = {
            "user_id": user_id,
            "endpoint": payload.endpoint,
            "keys": payload.keys.model_dump(),
            "user_agent": payload.user_agent,
            "created_at": datetime.utcnow().isoformat()
        }
        res = supabase.table("push_subscriptions").upsert(record, on_conflict="user_id,endpoint").execute()
        
        sub_id = res.data[0]["id"] if (res.data and len(res.data) > 0) else "registered"
        return {
            "status": "success",
            "subscription_id": str(sub_id)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to subscribe push notifications: {str(e)}")

@router.post("/unsubscribe", status_code=status.HTTP_200_OK)
async def unsubscribe_push(
    endpoint: str,
    user_id: str = Depends(get_current_user)
):
    try:
        supabase.table("push_subscriptions").delete().eq("user_id", user_id).eq("endpoint", endpoint).execute()
        return {"status": "unsubscribed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to unsubscribe: {str(e)}")

@router.post("/test")
async def test_push_notification(
    payload: PushTestNotification,
    user_id: str = Depends(get_current_user)
):
    try:
        success = await send_push_notification(
            user_id=user_id,
            title=payload.title,
            body=payload.body,
            url=payload.url
        )
        if success:
            return {"status": "sent", "detail": "Notification sent successfully"}
        return {"status": "no_active_subscriptions", "detail": "No active subscriptions found or VAPID keys missing"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send test push: {str(e)}")
