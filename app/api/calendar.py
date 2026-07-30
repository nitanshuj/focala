import html as html_lib
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from typing import Optional, List

from app.dependencies import get_current_user
from app.config import settings
from app.models.calendar_connection import (
    CalendarConnectionStatus,
    CalendarSyncResponse,
    CreateCalendarEventRequest,
    UpdateCalendarEventRequest,
    GoogleCalendarEvent
)
from app.services.calendar_client import (
    get_authorization_url,
    exchange_code_and_store_tokens,
    get_connection_status,
    fetch_user_google_calendar_events,
    create_google_calendar_event,
    update_google_calendar_event,
    delete_google_calendar_event,
    disconnect_calendar
)

router = APIRouter(prefix="/calendar", tags=["Calendar"])

@router.get("/status", response_model=CalendarConnectionStatus)
async def get_calendar_status(user_id: str = Depends(get_current_user)):
    try:
        res = await get_connection_status(user_id)
        return CalendarConnectionStatus(
            connected=res["connected"],
            google_email=res.get("google_email"),
            connected_at=res.get("connected_at")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch calendar status: {str(e)}")

@router.get("/authorize")
async def authorize_calendar(user_id: str = Depends(get_current_user)):
    try:
        url = get_authorization_url(state=user_id)
        return {"authorization_url": url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate authorize URL: {str(e)}")

@router.get("/callback")
async def calendar_callback(
    code: str = Query(...),
    state: Optional[str] = Query(None)
):
    try:
        target_user_id = state or "00000000-0000-0000-0000-000000000000"
        result = await exchange_code_and_store_tokens(code, target_user_id)

        # H2 Fix: escape google_email before embedding in HTML to prevent XSS
        safe_email = html_lib.escape(result.get("google_email", ""))

        # H4 Fix: use FRONTEND_URL from settings instead of hardcoded localhost
        frontend_settings_url = f"{settings.FRONTEND_URL}/settings?calendar_connected=true"

        # H3 Fix: postMessage target origin locked to FRONTEND_URL (not "*")
        frontend_origin = settings.FRONTEND_URL

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Google Calendar Connected</title>
            <meta http-equiv="refresh" content="2;url={frontend_settings_url}" />
            <style>
                body {{ font-family: system-ui, sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; margin: 0; background: #090d16; color: #fff; text-align: center; }}
                .card {{ background: #131b2e; padding: 2rem; border-radius: 1rem; border: 1px solid #1e293b; max-width: 400px; }}
                .badge {{ color: #10b981; font-weight: bold; margin-bottom: 1rem; }}
                a {{ color: #3b82f6; text-decoration: none; font-size: 0.875rem; display: block; margin-top: 1rem; }}
            </style>
        </head>
        <body>
            <div class="card">
                <div class="badge">&#10003; Connected to Google Calendar</div>
                <h2>Success!</h2>
                <p>Account <strong>{safe_email}</strong> has been linked to FoCala.</p>
                <p style="font-size: 0.875rem; color: #94a3b8;">Redirecting back to FoCala settings...</p>
                <a href="{frontend_settings_url}">Click here if not redirected automatically</a>
            </div>
            <script>
                if (window.opener) {{
                    window.opener.postMessage(
                        {{"type": "GOOGLE_CALENDAR_CONNECTED", "email": "{safe_email}"}},
                        "{frontend_origin}"
                    );
                }}
                setTimeout(function() {{ window.close(); }}, 3000);
            </script>
        </body>
        </html>
        """
        from fastapi.responses import HTMLResponse
        return HTMLResponse(content=html_content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to complete OAuth callback: {str(e)}")

@router.get("/events", response_model=CalendarSyncResponse)
async def get_calendar_events(
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    user_id: str = Depends(get_current_user)
):
    try:
        events = await fetch_user_google_calendar_events(user_id, start_time=start, end_time=end)
        return CalendarSyncResponse(
            synced_events_count=len(events),
            events=events
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch calendar events: {str(e)}")

@router.post("/events", response_model=GoogleCalendarEvent, status_code=status.HTTP_201_CREATED)
async def create_calendar_event_endpoint(
    payload: CreateCalendarEventRequest,
    user_id: str = Depends(get_current_user)
):
    try:
        event = await create_google_calendar_event(user_id, payload.model_dump())
        return GoogleCalendarEvent(**event)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create Google Calendar event: {str(e)}")

@router.patch("/events/{event_id}", response_model=GoogleCalendarEvent)
async def update_calendar_event_endpoint(
    event_id: str,
    payload: UpdateCalendarEventRequest,
    user_id: str = Depends(get_current_user)
):
    try:
        event = await update_google_calendar_event(user_id, event_id, payload.model_dump(exclude_unset=True))
        return GoogleCalendarEvent(**event)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update Google Calendar event: {str(e)}")

@router.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_calendar_event_endpoint(
    event_id: str,
    user_id: str = Depends(get_current_user)
):
    try:
        await delete_google_calendar_event(user_id, event_id)
        return None
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete Google Calendar event: {str(e)}")

@router.delete("/disconnect", status_code=status.HTTP_200_OK)
async def disconnect_calendar_endpoint(user_id: str = Depends(get_current_user)):
    try:
        ok = await disconnect_calendar(user_id)
        if ok:
            return {"status": "disconnected", "message": "Google Calendar disconnected successfully"}
        raise HTTPException(status_code=400, detail="Failed to disconnect calendar")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to disconnect calendar: {str(e)}")
