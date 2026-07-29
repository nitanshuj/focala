# Technical Implementation Plan & Architecture Specification

---

## 1. System Architecture Overview

The system operates on a hybrid client-server architecture:
- **Frontend Layer**: PWA built with React, Vite (`vite-plugin-pwa`), and Tailwind CSS. Service Workers handle offline caching, push listening, and notification interactions.
- **Backend Service Layer**: FastAPI Python application hosted on Render, serving as an API gateway for AI workflows, scheduler events, and Push Notification delivery.
- **Data & Auth Layer**: Supabase PostgreSQL database equipped with Row Level Security (RLS) policies and JWT authentication.

```
┌─────────────────────────────────────────────────────────┐
│                      CLIENT LAYER                       │
│  ┌───────────────────┐    ┌──────────────────────────┐  │
│  │   React/Vite App  │    │  PWA (ChromeOS / Win 11) │  │
│  │   - Tailwind CSS  │    │  - Service Worker (sw.js)│  │
│  │   - Zustand State │    │  - Offline Cache & Sync  │  │
│  └─────────┬─────────┘    └────────────┬─────────────┘  │
│            │        HTTPS REST API     │                │
└────────────┼───────────────────────────┼────────────────┘
             │                           │
             ▼                           ▼
┌─────────────────────────────────────────────────────────┐
│                    BACKEND (FastAPI)                    │
│  ┌──────────────┐    ┌─────────────┐   ┌─────────────┐  │
│  │ Tasks API    │    │ APScheduler │   │ Push Engine │  │
│  │ - Breakdown  │    │ - Daily 7AM │   │ (pywebpush) │  │
│  │ - Rollover   │    │ - Nudges    │   │ - VAPID     │  │
│  │ - Reverse    │    └──────┬──────┘   └──────┬──────┘  │
│  └──────┬───────┘           │                 │         │
│         │        ┌──────────▼──────────┐      │         │
│         │        │  Gemini 2.0 Client  │      │         │
│         │        │  - Task breakdown   │      │         │
│         │        │  - Schedule plan    │      │         │
│         │        └─────────────────────┘      │         │
└─────────┼─────────────────────────────────────┼─────────┘
          │                                     │
          ▼                                     ▼
┌─────────────────────────────────────────────────────────┐
│                    DATA LAYER (Supabase)                │
│  PostgreSQL | Auth | Storage                            │
│  Tables: profiles, tasks, routines, routine_completions, │
│          daily_plans, brain_dumps, push_subscriptions,  │
│          mood_logs, focus_sessions                      │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Implemented Backend Architecture & Code Structure

The FastAPI codebase is structured as follows:

```
focala/
├── app/
│   ├── api/
│   │   ├── tasks.py          # Task CRUD, Gemini breakdown, Rollover, Reverse summary
│   │   ├── brain_dump.py     # Brain dump inbox & Gemini triage into tasks
│   │   ├── planning.py       # Daily plan generation & mid-day rebalancing
│   │   ├── routines.py       # Routine checklists & step completions
│   │   ├── focus.py          # Focus sessions & virtual body doubling rooms
│   │   ├── mood.py           # Energy check-ins & trend analytics
│   │   ├── calendar.py       # Google Calendar event synchronization
│   │   ├── push.py           # Web push subscriptions & test endpoints
│   │   └── router.py         # Main aggregated router mounted at /api
│   ├── models/
│   │   ├── task.py           # Pydantic schemas (Task, Breakdown, Reverse Summary)
│   │   ├── plan.py           # Daily Schedule schemas (ScheduleBlock, DailyPlan)
│   │   ├── routine.py        # Routine templates & step completion schemas
│   │   ├── focus.py          # Focus log & room schemas
│   │   ├── mood.py           # Mood log & Energy trend schemas
│   │   └── push.py           # Push registration schemas
│   ├── services/
│   │   ├── gemini_client.py  # Gemini 2.0 Flash integration & ADHD prompt logic
│   │   ├── push_service.py   # pywebpush Web Push sender with auto 410 cleanup
│   │   ├── supabase_client.py# Supabase Python SDK client setup
│   │   └── calendar_client.py# Google Calendar sync client
│   ├── scheduler/
│   │   └── daily_planner.py  # APScheduler daily jobs & transition reminders
│   ├── utils/
│   │   └── auth.py           # Supabase JWT token verification
│   ├── config.py             # pydantic-settings environment variables
│   ├── dependencies.py       # FastAPI get_current_user security dependency
│   └── main.py               # Application entrypoint & CORS middleware
├── implementation_plan/      # Technical & concept documentation
├── render.yaml               # Infrastructure as Code specification
├── pyproject.toml            # Dependencies & package specification
└── requirements.txt          # Python dependencies requirements file
```

---

## 3. Implemented Database Schema (Supabase PostgreSQL)

### 3.1 `profiles`
Stores user settings and ADHD scheduling preferences.
- `id`: `UUID` (Primary key, references `auth.users.id`)
- `energy_pattern`: `VARCHAR` (`morning_peak`, `afternoon_peak`, `night_owl`, `flexible`)
- `gemini_enabled`: `BOOLEAN` (Default `TRUE`)
- `created_at`: `TIMESTAMPTZ`

### 3.2 `tasks`
Core task table supporting micro-steps and rollover tracking.
- `id`: `UUID` (Primary key)
- `user_id`: `UUID` (Foreign key to `profiles.id`)
- `title`: `TEXT`
- `description`: `TEXT` (Optional)
- `status`: `VARCHAR` (`pending`, `in_progress`, `done`, `parked`)
- `priority`: `VARCHAR` (`low`, `medium`, `high`, `urgent`)
- `energy_level`: `VARCHAR` (`low`, `medium`, `high`)
- `estimated_minutes`: `INTEGER` (Default `30`)
- `actual_minutes`: `INTEGER`
- `scheduled_start`: `TIMESTAMPTZ`
- `scheduled_end`: `TIMESTAMPTZ`
- `parent_task_id`: `UUID` (Self reference for micro-steps)
- `is_micro_step`: `BOOLEAN` (Default `FALSE`)
- `ai_generated`: `BOOLEAN` (Default `FALSE`)
- `rolled_over_count`: `INTEGER` (Default `0`)
- `completed_at`: `TIMESTAMPTZ`
- `created_at`: `TIMESTAMPTZ`

### 3.3 `brain_dumps`
Frictionless inbox entries for instant thought dumping.
- `id`: `UUID` (Primary key)
- `user_id`: `UUID`
- `content`: `TEXT`
- `triaged`: `BOOLEAN` (Default `FALSE`)
- `converted_task_id`: `UUID`
- `created_at`: `TIMESTAMPTZ`

### 3.4 `daily_plans`
Stores Gemini-generated daily focus schedules.
- `id`: `UUID` (Primary key)
- `user_id`: `UUID`
- `plan_date`: `DATE` (Unique with `user_id`)
- `schedule`: `JSONB` (Contains `schedule`, `parked_tasks`, `daily_focus`, `encouragement`)
- `raw_gemini_response`: `TEXT`
- `created_at`: `TIMESTAMPTZ`

### 3.5 `routines` & `routine_completions`
Pre-built or custom habits with streak tracking.
- `routines`: `id`, `user_id`, `title`, `steps` (`JSONB`), `target_time`, `active`
- `routine_completions`: `id`, `user_id`, `routine_id`, `completed_steps` (`JSONB`), `completed_at` (`DATE`)

### 3.6 `focus_sessions`
Body doubling logs and focus timer analytics.
- `id`: `UUID` (Primary key)
- `user_id`: `UUID`
- `duration_minutes`: `INTEGER`
- `task_id`: `UUID` (Optional link to `tasks.id`)
- `ambient_mode`: `VARCHAR` (`white_noise`, `soundscape`, `body_double`, `cafe`)
- `logged_at`: `TIMESTAMPTZ`

### 3.7 `mood_logs`
Lightweight energy check-in records.
- `id`: `UUID` (Primary key)
- `user_id`: `UUID`
- `energy_level`: `INTEGER` (1 to 5 scale)
- `mood`: `VARCHAR`
- `note`: `TEXT`
- `logged_at`: `TIMESTAMPTZ`

### 3.8 `push_subscriptions`
Web Push API device endpoint store.
- `id`: `UUID` (Primary key)
- `user_id`: `UUID`
- `endpoint`: `TEXT` (Unique with `user_id`)
- `keys`: `JSONB` (`p256dh`, `auth`)
- `user_agent`: `TEXT`
- `created_at`: `TIMESTAMPTZ`

---

## 4. API Endpoints Specification

For complete request models, parameters, HTTP methods, and response schemas for all 8 API modules, see the dedicated [api_endpoints.md](file:///c:/Products-Projects/Focala/code/focala/implementation_plan/api_endpoints.md) document.

Summary of available routers mounted under `/api`:
- **Tasks & Micro-steps** (`/api/tasks`) — Task CRUD, Gemini task breakdown, rollover, and reverse to-do summary.
- **Brain Dump** (`/api/brain-dumps`) — Inbox capture and Gemini task triage.
- **Daily Planning** (`/api/plan`) — AI schedule generation, today's schedule view, and mid-day rebalancing.
- **Focus & Body Doubling** (`/api/focus`) — Focus timer session logger and virtual body doubling rooms.
- **Routines & Habit Checklist** (`/api/routines`) — Routines management and step completion logs.
- **Energy & Mood** (`/api/mood`) — Energy check-ins and 30-day analytics trends.
- **Push Notifications** (`/api/push`) — Subscription registration, removal, and test delivery.
- **Calendar** (`/api/calendar`) — Google Calendar event synchronization.

---

## 5. Background Jobs & Push Engine

### 5.1 APScheduler (`app/scheduler/daily_planner.py`)
- **Daily 7:00 AM Job**: Calls `generate_daily_plan()` for active users and sends schedule push notification.
- **5-Minute Transition Nudges**: Checks upcoming schedule blocks and sends gentle reminder alerts.
- **Evening 8:00 PM Check-in**: Prompts user for brief mood/energy check-in.

### 5.2 Push Notification Engine (`app/services/push_service.py`)
- Uses `pywebpush` with VAPID key pairs.
- Automatically handles HTTP `410 Gone` expired subscriptions by pruning invalid endpoints from the database.

---

## 6. Infrastructure & Deployment (`render.yaml`)

```yaml
services:
  - type: web
    name: focala-api
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: SUPABASE_URL
        sync: false
      - key: SUPABASE_SERVICE_KEY
        sync: false
      - key: GEMINI_API_KEY
        sync: false
      - key: VAPID_PRIVATE_KEY
        sync: false
      - key: VAPID_PUBLIC_KEY
        sync: false
      - key: JWT_SECRET
        sync: false
```