import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import os

from app.config import settings
from app.services.supabase_client import supabase

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar"]

def get_google_auth_flow():
    from google_auth_oauthlib.flow import Flow
    client_id = settings.GOOGLE_CLIENT_ID or "placeholder_client_id"
    client_secret = settings.GOOGLE_CLIENT_SECRET or "placeholder_client_secret"
    redirect_uri = settings.GOOGLE_REDIRECT_URI or "http://localhost:8000/api/calendar/callback"

    client_config = {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uris": [redirect_uri],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    flow = Flow.from_client_config(client_config, scopes=SCOPES)
    flow.redirect_uri = redirect_uri
    return flow

def get_authorization_url(state: Optional[str] = None) -> str:
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        # Development fallback redirect
        mock_state = f"&state={state}" if state else ""
        return f"http://localhost:8000/api/calendar/callback?code=mock_dev_code{mock_state}"
    try:
        flow = get_google_auth_flow()
        authorization_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
            state=state
        )
        return authorization_url
    except Exception as e:
        logger.error(f"Error generating OAuth authorization URL: {e}")
        mock_state = f"&state={state}" if state else ""
        return f"http://localhost:8000/api/calendar/callback?code=mock_dev_code{mock_state}"

MOCK_CONNECTIONS: Dict[str, Dict[str, Any]] = {}

async def exchange_code_and_store_tokens(code: str, user_id: str) -> Dict[str, Any]:
    if code == "mock_dev_code" or not settings.GOOGLE_CLIENT_ID:
        mock_record = {
            "user_id": user_id,
            "google_email": f"dev-user-{user_id[:6]}@gmail.com",
            "access_token": "mock_access_token",
            "refresh_token": "mock_refresh_token",
            "token_expiry": datetime.now(timezone.utc).isoformat(),
            "connected_at": datetime.now(timezone.utc).isoformat()
        }
        MOCK_CONNECTIONS[user_id] = mock_record
        try:
            supabase.table("calendar_connections").upsert(mock_record, on_conflict="user_id").execute()
        except Exception as e:
            logger.warning(f"Supabase upsert warning for mock calendar connection: {e}")
        return {"status": "connected", "google_email": mock_record["google_email"]}

    try:
        from googleapiclient.discovery import build
        flow = get_google_auth_flow()
        flow.fetch_token(code=code)
        credentials = flow.credentials

        service = build("calendar", "v3", credentials=credentials)
        user_info = service.calendars().get(calendarId="primary").execute()
        google_email = user_info.get("id") or user_info.get("summary", "google_user@calendar.com")

        record = {
            "user_id": user_id,
            "google_email": google_email,
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token or "",
            "token_expiry": credentials.expiry.isoformat() if credentials.expiry else datetime.now(timezone.utc).isoformat(),
            "connected_at": datetime.now(timezone.utc).isoformat()
        }
        MOCK_CONNECTIONS[user_id] = record
        try:
            supabase.table("calendar_connections").upsert(record, on_conflict="user_id").execute()
        except Exception as db_err:
            logger.warning(f"Supabase calendar_connections table insert warning: {db_err}")
        return {"status": "connected", "google_email": google_email}
    except Exception as e:
        logger.error(f"Failed to exchange Google OAuth code: {e}")
        raise RuntimeError(f"Google OAuth token exchange failed: {str(e)}")

async def get_connection_status(user_id: str) -> Dict[str, Any]:
    if user_id in MOCK_CONNECTIONS:
        conn = MOCK_CONNECTIONS[user_id]
        return {
            "connected": True,
            "google_email": conn.get("google_email"),
            "connected_at": conn.get("connected_at")
        }

    try:
        res = supabase.table("calendar_connections").select("*").eq("user_id", user_id).execute()
        if res.data and len(res.data) > 0:
            conn = res.data[0]
            return {
                "connected": True,
                "google_email": conn.get("google_email"),
                "connected_at": conn.get("connected_at")
            }
    except Exception as e:
        logger.warning(f"Failed to check calendar connection status: {e}")
    return {"connected": False, "google_email": None, "connected_at": None}

async def fetch_user_google_calendar_events(user_id: str, start_time: Optional[str] = None, end_time: Optional[str] = None) -> List[Dict[str, Any]]:
    status = await get_connection_status(user_id)
    if not status.get("connected"):
        return []

    try:
        res = supabase.table("calendar_connections").select("*").eq("user_id", user_id).execute()
        if not res.data:
            return []
        conn = res.data[0]

        if conn.get("access_token") == "mock_access_token" or not settings.GOOGLE_CLIENT_ID:
            return [
                {
                    "id": "mock-event-1",
                    "summary": "Team Sync & Planning",
                    "description": "Daily standup meeting",
                    "start_time": start_time or datetime.now(timezone.utc).isoformat(),
                    "end_time": end_time or datetime.now(timezone.utc).isoformat(),
                    "location": "Google Meet"
                }
            ]

        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build

        credentials = Credentials(
            token=conn["access_token"],
            refresh_token=conn.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
        )

        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
            supabase.table("calendar_connections").update({
                "access_token": credentials.token,
                "token_expiry": credentials.expiry.isoformat() if credentials.expiry else datetime.now(timezone.utc).isoformat()
            }).eq("user_id", user_id).execute()

        service = build("calendar", "v3", credentials=credentials)
        time_min = start_time or datetime.now(timezone.utc).replace(hour=0, minute=0, second=0).isoformat()
        time_max = end_time or datetime.now(timezone.utc).replace(hour=23, minute=59, second=59).isoformat()

        events_result = service.events().list(
            calendarId="primary",
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy="startTime"
        ).execute()

        raw_items = events_result.get("items", [])
        formatted_events = []
        for item in raw_items:
            start_val = item.get("start", {}).get("dateTime") or item.get("start", {}).get("date", "")
            end_val = item.get("end", {}).get("dateTime") or item.get("end", {}).get("date", "")
            formatted_events.append({
                "id": item.get("id"),
                "summary": item.get("summary", "Untitled Event"),
                "description": item.get("description"),
                "start_time": start_val,
                "end_time": end_val,
                "location": item.get("location")
            })
        return formatted_events
    except Exception as e:
        logger.error(f"Failed to fetch Google Calendar events: {e}")
        return []

async def create_google_calendar_event(user_id: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
    status = await get_connection_status(user_id)
    if not status.get("connected") and settings.GOOGLE_CLIENT_ID:
        raise RuntimeError("Google Calendar is not connected.")

    res = supabase.table("calendar_connections").select("*").eq("user_id", user_id).execute()
    conn = res.data[0] if res.data else {}
    if conn.get("access_token") == "mock_access_token" or not settings.GOOGLE_CLIENT_ID or not res.data:
        return {
            "id": f"dev-event-{int(datetime.now().timestamp())}",
            "summary": event_data.get("summary", "New Task Event"),
            "description": event_data.get("description", ""),
            "start_time": event_data.get("start_time", datetime.now().isoformat()),
            "end_time": event_data.get("end_time", datetime.now().isoformat()),
            "location": event_data.get("location")
        }

    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    credentials = Credentials(
        token=conn["access_token"],
        refresh_token=conn.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
    )
    service = build("calendar", "v3", credentials=credentials)
    body = {
        "summary": event_data["summary"],
        "description": event_data.get("description"),
        "start": {"dateTime": event_data["start_time"]},
        "end": {"dateTime": event_data["end_time"]},
        "location": event_data.get("location")
    }
    created = service.events().insert(calendarId="primary", body=body).execute()
    return {
        "id": created.get("id"),
        "summary": created.get("summary"),
        "description": created.get("description"),
        "start_time": created.get("start", {}).get("dateTime"),
        "end_time": created.get("end", {}).get("dateTime"),
        "location": created.get("location")
    }

async def update_google_calendar_event(user_id: str, event_id: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
    status = await get_connection_status(user_id)
    if not status.get("connected") and settings.GOOGLE_CLIENT_ID:
        raise RuntimeError("Google Calendar is not connected.")

    res = supabase.table("calendar_connections").select("*").eq("user_id", user_id).execute()
    conn = res.data[0] if res.data else {}
    if conn.get("access_token") == "mock_access_token" or not settings.GOOGLE_CLIENT_ID or not res.data:
        return {
            "id": event_id,
            "summary": event_data.get("summary", "Updated Event"),
            "description": event_data.get("description", ""),
            "start_time": event_data.get("start_time", datetime.now().isoformat()),
            "end_time": event_data.get("end_time", datetime.now().isoformat())
        }

    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    credentials = Credentials(
        token=conn["access_token"],
        refresh_token=conn.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
    )
    service = build("calendar", "v3", credentials=credentials)
    patch_body = {}
    if "summary" in event_data: patch_body["summary"] = event_data["summary"]
    if "description" in event_data: patch_body["description"] = event_data["description"]
    if "start_time" in event_data: patch_body["start"] = {"dateTime": event_data["start_time"]}
    if "end_time" in event_data: patch_body["end"] = {"dateTime": event_data["end_time"]}
    if "location" in event_data: patch_body["location"] = event_data["location"]

    updated = service.events().patch(calendarId="primary", eventId=event_id, body=patch_body).execute()
    return {
        "id": updated.get("id"),
        "summary": updated.get("summary"),
        "description": updated.get("description"),
        "start_time": updated.get("start", {}).get("dateTime"),
        "end_time": updated.get("end", {}).get("dateTime")
    }

async def delete_google_calendar_event(user_id: str, event_id: str) -> bool:
    status = await get_connection_status(user_id)
    if not status.get("connected"):
        return True

    try:
        res = supabase.table("calendar_connections").select("*").eq("user_id", user_id).execute()
        conn = res.data[0] if (res.data and len(res.data) > 0) else {}
        if conn.get("access_token") == "mock_access_token" or not settings.GOOGLE_CLIENT_ID or not conn:
            return True
    except Exception:
        return True

    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    credentials = Credentials(
        token=conn["access_token"],
        refresh_token=conn.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
    )
    service = build("calendar", "v3", credentials=credentials)
    service.events().delete(calendarId="primary", eventId=event_id).execute()
    return True

async def disconnect_calendar(user_id: str) -> bool:
    if user_id in MOCK_CONNECTIONS:
        MOCK_CONNECTIONS.pop(user_id, None)
    try:
        supabase.table("calendar_connections").delete().eq("user_id", user_id).execute()
        return True
    except Exception as e:
        logger.error(f"Failed to disconnect Google Calendar: {e}")
        return True
