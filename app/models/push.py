from pydantic import BaseModel
from typing import Dict, Any, Optional

class PushKeys(BaseModel):
    p256dh: str
    auth: str

class PushSubscribeRequest(BaseModel):
    endpoint: str
    keys: PushKeys
    user_agent: Optional[str] = None

class PushSubscribeResponse(BaseModel):
    status: str
    subscription_id: str

class PushTestNotification(BaseModel):
    title: str = "Test Notification"
    body: str = "This is a test notification from FoCala!"
    url: str = "/today"
