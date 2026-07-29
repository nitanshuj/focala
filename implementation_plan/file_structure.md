# File Structure

FOCALA/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app instance, lifespan, middleware
│   ├── config.py               # Environment variables, settings
│   ├── dependencies.py         # Auth, user context, DB clients
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── router.py           # Main APIRouter that includes all sub-routers
│   │   ├── tasks.py            # Task CRUD endpoints
│   │   ├── brain_dump.py       # Brain dump endpoints
│   │   ├── routines.py         # Routine management
│   │   ├── planning.py         # Gemini daily planning endpoints
│   │   ├── calendar.py         # Google Calendar OAuth + events
│   │   └── push.py             # Push notification subscription + send
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── supabase_client.py  # Supabase client initialization
│   │   ├── gemini_client.py    # Gemini API client + planning logic
│   │   ├── calendar_client.py  # Google Calendar API + token refresh
│   │   └── push_service.py     # pywebpush helper functions
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── task.py             # Pydantic schemas for tasks
│   │   ├── routine.py          # Pydantic schemas for routines
│   │   └── calendar.py         # Pydantic schemas for calendar events
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── auth.py             # JWT verification for Supabase Auth
│   │   └── encryption.py       # Token encryption helpers
│   │
│   └── scheduler/
│       ├── __init__.py
│       └── daily_planner.py    # APScheduler cron job for daily planning
│
├── requirements.txt            # All Python dependencies
├── render.yaml                 # Render infrastructure config (optional)
├── .env.example                # Template for environment variables
└── README.md                   # Setup instructions