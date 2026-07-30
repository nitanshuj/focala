# Push Notification Subsystem (VAPID / WebPush) - Commented Out
# from pywebpush import webpush, WebPushException
# import json
# import logging
# from datetime import datetime
# from app.config import settings
# from app.services.supabase_client import supabase

# logger = logging.getLogger(__name__)

async def send_push_notification(user_id: str, title: str, body: str, url: str = "/today", tag: str = "default") -> bool:
    """
    Push notifications disabled for now.
    """
    return False

# async def send_push_notification_disabled(user_id: str, title: str, body: str, url: str = "/today", tag: str = "default") -> bool:
#     if not settings.VAPID_PRIVATE_KEY or not settings.VAPID_PUBLIC_KEY:
#         logger.warning("VAPID keys not configured. Push notification skipped.")
#         return False
#
#     vapid_claims = {"sub": f"mailto:{settings.VAPID_CLAIMS_EMAIL}"}
#
#     try:
#         res = supabase.table("push_subscriptions").select("*").eq("user_id", user_id).execute()
#         subscriptions = res.data or []
#         if not subscriptions:
#             logger.info(f"No push subscriptions found for user {user_id}")
#             return False
#
#         payload = json.dumps({
#             "title": title,
#             "body": body,
#             "url": url,
#             "tag": tag,
#             "timestamp": int(datetime.utcnow().timestamp())
#         })
#
#         success_count = 0
#         for sub in subscriptions:
#             try:
#                 webpush(
#                     subscription_info={
#                         "endpoint": sub["endpoint"],
#                         "keys": sub["keys"]
#                     },
#                     data=payload,
#                     vapid_private_key=settings.VAPID_PRIVATE_KEY,
#                     vapid_claims=vapid_claims
#                 )
#                 success_count += 1
#             except WebPushException as e:
#                 logger.warning(f"Web Push exception for sub {sub.get('id')}: {e}")
#                 if e.response is not None and e.response.status_code in (404, 410):
#                     logger.info(f"Subscription expired (410/404). Deleting sub {sub.get('id')}")
#                     supabase.table("push_subscriptions").delete().eq("id", sub["id"]).execute()
#             except Exception as e:
#                 logger.error(f"Unexpected push error: {e}")
#
#         return success_count > 0
#
#     except Exception as e:
#         logger.error(f"Failed to fetch push subscriptions for user {user_id}: {e}")
#         return False
