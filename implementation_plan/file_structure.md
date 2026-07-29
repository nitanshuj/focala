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
│   │   ├── tasks.py            # Task CRUD & micro-step breakdown endpoints
│   │   ├── brain_dump.py       # Brain dump capture & AI triage endpoints
│   │   ├── routines.py         # Routine management & completions
│   │   ├── planning.py         # Gemini daily planning & rebalance endpoints
│   │   ├── calendar.py         # Google Calendar OAuth + events
│   │   ├── push.py             # Push notification subscription + test endpoints
│   │   └── mood.py             # Energy check-in & trend analytics endpoints
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── supabase_client.py  # Supabase client initialization
│   │   ├── gemini_client.py    # Gemini API client + planning logic
│   │   ├── calendar_client.py  # Google Calendar API + token refresh
│   │   └── push_service.py     # pywebpush helper functions & expired sub cleanup
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── task.py             # Pydantic schemas for tasks & brain dump
│   │   ├── routine.py          # Pydantic schemas for routines
│   │   ├── plan.py             # Pydantic schemas for AI daily plans
│   │   ├── push.py             # Pydantic schemas for Web Push subscriptions
│   │   ├── mood.py             # Pydantic schemas for energy logs
│   │   └── calendar.py         # Pydantic schemas for calendar events
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── auth.py             # JWT verification for Supabase Auth
│   │   └── encryption.py       # Token encryption helpers
│   │
│   └── scheduler/
│       ├── __init__.py
│       └── daily_planner.py    # APScheduler jobs (7 AM planning, reminders, evening check-in)
│
├── implementation_plan/        # Project planning documentation
│   ├── database_design.md      # Supabase SQL schema design & RLS policies
│   ├── file_structure.md       # Repository directory tree documentation
│   ├── implementation_plan_1.md# Core architecture & design specification
│   └── current_implementation.md# System walkthrough & implementation status
│
├── pyproject.toml              # UV / PEP 621 project configuration & dependencies
├── .python-version             # Python target version (3.12)
├── requirements.txt            # Python requirements listing
├── render.yaml                 # Render infrastructure config
├── .env.example                # Template for environment variables
└── README.md                   # Setup instructions