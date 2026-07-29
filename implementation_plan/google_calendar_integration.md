Yes, **Google Calendar integration should be at the backend (FastAPI)** — here's why and how to do it:

## Why Backend for Google Calendar

OAuth2 token handling, secure storage of refresh tokens, and making API calls to Google's servers all belong on the backend, not in the frontend. Your PWA should never expose your Google API credentials or handle OAuth tokens directly. FastAPI will: [developers.google](https://developers.google.com/workspace/calendar/api/quickstart/python)

- Handle the OAuth2 authorization flow (redirect to Google → receive auth code → exchange for tokens)
- Store encrypted refresh tokens in Supabase (tied to user accounts via Row Level Security)
- Make authenticated API calls to fetch events, create events, etc.
- Refresh tokens automatically when they expire (using the stored refresh token)

## Integration Architecture

```
┌─────────────────────────────────────────────────┐
│                  PWA Frontend                    │
│                                                  │
│  - "Connect Google Calendar" button              │
│  - Redirects user to: /api/calendar/authorize    │
│  - Receives events from: GET /api/calendar/events│
│  - POST /api/calendar/events (create event)      │
└───────────────────┬─────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│              FastAPI Backend (Render)            │
│                                                  │
│  GET  /api/calendar/authorize → redirect to      │
│      Google OAuth consent screen                 │
│                                                  │
│  GET  /api/calendar/callback?code=... →          │
│      exchange code for tokens, store in DB       │
│                                                  │
│  GET  /api/calendar/events?start=...&end=... →   │
│      fetch events from Google API                │
│                                                  │
│  POST /api/calendar/events →                     │
│      create event in Google Calendar             │
│                                                  │
│  ┌────────────────────────────────────────────┐  │
│  │     google-auth-oauthlib, google-api-      │  │
│  │     python-client, refresh token logic     │  │
│  └────────────────────────────────────────────┘  │
└───────────────────┬─────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│          Supabase (user_id → tokens)             │
│                                                  │
│  Table: calendar_connections                     │
│  - user_id (uuid)                                │
│  - google_email (text)                           │
│  - access_token (encrypted text)                 │
│  - refresh_token (encrypted text)                │
│  - token_expiry (timestamptz)                    │
│  - connected_at (timestamptz)                    │
└─────────────────────────────────────────────────┘
```

## FastAPI Implementation

### 1. Install Required Packages

```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

### 2. Set Up Google Cloud Console

1. Enable **Google Calendar API** in your GCP project
2. Create **OAuth 2.0 Client ID** (Web application type)
3. Add authorized redirect URI: `https://yourapp.onrender.com/api/calendar/callback` (or `http://localhost:8000/api/calendar/callback` for dev)
4. Download `client_secret.json` and store credentials in environment variables:
   - `GOOGLE_CLIENT_ID`
   - `GOOGLE_CLIENT_SECRET`
   - `GOOGLE_REDIRECT_URI`

### 3. Supabase Schema

```sql
create table public.calendar_connections (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users on delete cascade unique,
  google_email text not null,
  access_token text not null,
  refresh_token text not null,
  token_expiry timestamptz not null,
  connected_at timestamptz default now()
);

-- RLS: users can only see their own connections
alter table public.calendar_connections enable row level security;
create policy "Users see own calendar connections" on public.calendar_connections
  for all using (auth.uid() = user_id);
```

### 4. FastAPI Endpoints

```python
from fastapi import APIRouter, HTTPException, Query
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from datetime import datetime, timedelta
import json

router = APIRouter(prefix="/api/calendar")

SCOPES = ["https://www.googleapis.com/auth/calendar"]

def get_flow():
    return Flow.from_client_config({
        "web": {
            "client_id": os.environ["GOOGLE_CLIENT_ID"],
            "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
            "redirect_uris": [os.environ["GOOGLE_REDIRECT_URI"]],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }, SCOPES)

@router.get("/authorize")
async def authorize_calendar():
    """Redirect user to Google OAuth consent screen"""
    flow = get_flow()
    flow.redirect_uri = os.environ["GOOGLE_REDIRECT_URI"]
    authorization_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent"
    )
    return {"authorization_url": authorization_url}

@router.get("/callback")
async def calendar_callback(code: str):
    """
    Handle OAuth callback from Google.
    Store tokens in Supabase tied to current user.
    """
    flow = get_flow()
    flow.redirect_uri = os.environ["GOOGLE_REDIRECT_URI"]
    flow.fetch_token(code=code)
    
    credentials = flow.credentials
    # Extract user's email from token info
    service = build("calendar", "v3", credentials=credentials)
    user_info = service.calendars().get(calendarId="primary").execute()
    google_email = user_info.get("id")
    
    # Store encrypted tokens in Supabase
    await supabase.from_("calendar_connections").upsert({
        "user_id": current_user_id,  # From JWT middleware
        "google_email": google_email,
        "access_token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_expiry": credentials.expiry.isoformat()
    }).execute()
    
    return {"message": "Calendar connected", "email": google_email}

@router.get("/events")
async def get_calendar_events(
    start: str = Query(...),
    end: str = Query(...)
):
    """Fetch events from user's Google Calendar"""
    # Get tokens from Supabase
    conn = await supabase.from_("calendar_connections").select("*").eq(
        "user_id", current_user_id
    ).single().execute()
    
    if not conn.data:
        raise HTTPException(400, "Calendar not connected")
    
    credentials = Credentials(
        token=conn.data["access_token"],
        refresh_token=conn.data["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
    )
    
    # Refresh if expired
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
        # Update tokens in DB
        await supabase.from_("calendar_connections").update({
            "access_token": credentials.token,
            "token_expiry": credentials.expiry.isoformat()
        }).eq("user_id", current_user_id).execute()
    
    service = build("calendar", "v3", credentials=credentials)
    events_result = service.events().list(
        calendarId="primary",
        timeMin=start,
        timeMax=end,
        singleEvents=True,
        orderBy="startTime"
    ).execute()
    
    return events_result.get("items", [])

@router.post("/events")
async def create_calendar_event(event: dict):
    """Create a new event in Google Calendar"""
    # Similar token retrieval/refresh logic as above
    ...
    service = build("calendar", "v3", credentials=credentials)
    event = service.events().insert(
        calendarId="primary",
        body=event
    ).execute()
    return event

@router.delete("/disconnect")
async def disconnect_calendar():
    """Remove calendar connection"""
    await supabase.from_("calendar_connections").delete().eq(
        "user_id", current_user_id
    ).execute()
    return {"message": "Calendar disconnected"}
```

### 5. Frontend PWA Integration

In your PWA, the flow is:

```javascript
// 1. User clicks "Connect Google Calendar"
const handleConnect = async () => {
  // 2. Fetch authorization URL from your backend
  const { authorization_url } = await fetch('/api/calendar/authorize').then(r => r.json());
  // 3. Redirect user to Google OAuth
  window.location.href = authorization_url;
};

// 4. After OAuth callback, backend redirects back to your app
// (e.g., /today?calendar_connected=true)
// You can show a success message and fetch initial events
```

Then fetch and display events:

```javascript
// Fetch events for the current day
const start = new Date().toISOString();
const end = new Date(new Date().setHours(23, 59, 59, 999)).toISOString();
const events = await fetch(`/api/calendar/events?start=${start}&end=${end}`).then(r => r.json());
// Render events in your daily planner view
```

## Key Considerations

- **Token Security** — Encrypt tokens before storing in Supabase using `pgcrypto` or a Python encryption library (e.g., `cryptography`) [joshuaakanetuk](https://joshuaakanetuk.com/blog/how-to-use-google-calendar-py/)
- **Token Refresh Logic** — Google access tokens expire in 1 hour; you must refresh using the stored refresh token before each API call if expired [developers.google](https://developers.google.com/workspace/calendar/api/quickstart/python)
- **Scopes** — Use `https://www.googleapis.com/auth/calendar` for full read/write access, or `https://www.googleapis.com/auth/calendar.readonly` if you only need to fetch events
- **Error Handling** — Handle cases where the user revokes access, tokens become invalid, or the API rate limits you
- **Daily Sync with Gemini** — When generating the daily plan, fetch Google Calendar events first and include them in the Gemini context so the AI can avoid scheduling conflicts and respect existing meetings 