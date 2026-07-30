# Technical Implementation Specification — FoCala Backend

## 1. Executive Summary & Tech Stack Overview
FoCala is an ADHD-friendly daily planning backend engineered with high responsiveness, minimal cognitive friction, and resilient fallback execution.

- **Core Framework**: FastAPI 0.115+ (Python 3.12+), utilizing async/await endpoints and Lifespan event handlers.
- **Database & Authentication**: Supabase (PostgreSQL 15+) with Row Level Security (RLS) policies and JWT bearer validation.
- **AI Intelligence**: Google Gemini 2.0 Flash API (`google-generativeai`) with structured JSON schema enforcement.
- **Push Engine**: `pywebpush` using Voluntary Application Server Identification (VAPID) keys for Web Push Protocol RFC 8030.
- **Background Scheduler**: `APScheduler` (AsyncIOScheduler) running in-process for automated morning planning & reminders.
- **Deployment Platform**: Render / Docker containerized service.

---

## 2. Data Model & Database Schema (Supabase PostgreSQL)

### 2.1 Table Specifications
```sql
-- Profiles Table
CREATE TABLE public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT UNIQUE NOT NULL,
    display_name TEXT,
    peak_energy_window TEXT DEFAULT '09:00-12:00',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tasks Table
CREATE TABLE public.tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_path(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    priority TEXT CHECK (priority IN ('low', 'medium', 'high')) DEFAULT 'medium',
    energy_level TEXT CHECK (energy_level IN ('low', 'medium', 'high')) DEFAULT 'medium',
    estimated_minutes INT DEFAULT 30,
    status TEXT CHECK (status IN ('backlog', 'today', 'in_progress', 'completed', 'parked')) DEFAULT 'backlog',
    due_date DATE,
    micro_steps JSONB DEFAULT '[]'::jsonb,
    is_recurring BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Routines & Routine Completions
CREATE TABLE public.routines (
    id UUID PRIMARY KEY DEFAULT gen_random_path(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    time_of_day TEXT CHECK (time_of_day IN ('morning', 'afternoon', 'evening')) DEFAULT 'morning',
    target_time TIME,
    estimated_minutes INT DEFAULT 15,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE public.routine_completions (
    id UUID PRIMARY KEY DEFAULT gen_random_path(),
    routine_id UUID NOT NULL REFERENCES public.routines(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    completed_date DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Brain Dumps Table
CREATE TABLE public.brain_dumps (
    id UUID PRIMARY KEY DEFAULT gen_random_path(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    raw_content TEXT NOT NULL,
    status TEXT CHECK (status IN ('unprocessed', 'processed')) DEFAULT 'unprocessed',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Daily Plans Table
CREATE TABLE public.daily_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_path(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    plan_date DATE NOT NULL DEFAULT CURRENT_DATE,
    schedule JSONB NOT NULL DEFAULT '[]'::jsonb,
    parked_tasks JSONB DEFAULT '[]'::jsonb,
    daily_focus TEXT,
    encouragement TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Push Subscriptions Table
CREATE TABLE public.push_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_path(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    endpoint TEXT UNIQUE NOT NULL,
    p256dh TEXT NOT NULL,
    auth TEXT NOT NULL,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Mood Logs & Focus Sessions
CREATE TABLE public.mood_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_path(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    energy_level INT CHECK (energy_level BETWEEN 1 AND 5),
    mood_score INT CHECK (mood_score BETWEEN 1 AND 5),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE public.focus_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_path(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    task_id UUID REFERENCES public.tasks(id) ON DELETE SET NULL,
    duration_minutes INT NOT NULL,
    completed BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 2.2 Row Level Security (RLS) Policy Pattern
```sql
ALTER TABLE public.tasks ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users access own tasks" ON public.tasks 
    FOR ALL USING (auth.uid() = user_id);
```

---

## 3. Core Architecture & Layer Interaction

```
┌────────────────────────────────────────────────────────────────────────┐
│                        FastAPI Application (app/main.py)              │
│                                                                        │
│   ┌────────────────────┐    ┌────────────────────┐   ┌──────────────┐  │
│   │ HTTPBearer Auth    │    │ CORS Middleware    │   │ APScheduler  │  │
│   │ (JWT Verification) │    │ (Origins: *)       │   │ (Lifespan)   │  │
│   └─────────┬──────────┘    └─────────┬──────────┘   └──────┬───────┘  │
└─────────────┼─────────────────────────┼─────────────────────┼──────────┘
              │                         │                     │
              ▼                         ▼                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│                       API Routers (app/api/*.py)                       │
│  - tasks.py        - brain_dump.py     - planning.py                   │
│  - routines.py     - mood.py           - focus.py                      │
│  - calendar.py     - push.py                                           │
└─────────────┬─────────────────────────┬─────────────────────┬──────────┘
              │                         │                     │
              ▼                         ▼                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│                      Services (app/services/*.py)                      │
│  - gemini_client.py   - push_service.py   - supabase_client.py       │
└─────────────┬─────────────────────────┬─────────────────────┬──────────┘
              │                         │                     │
              ▼                         ▼                     ▼
┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
│  Google Gemini 2.0  │  │  WebPush Protocol   │  │  Supabase PostgREST │
│  Flash API (AI)     │  │  (VAPID / pywebpush)│  │  (PostgreSQL DB)    │
└─────────────────────┘  └─────────────────────┘  └─────────────────────┘
```

---

## 4. API Endpoints Specification

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Application health diagnostic check | No |
| `GET` | `/api/tasks` | Fetch user tasks (optional status filter) | Yes |
| `POST` | `/api/tasks` | Create new task entry | Yes |
| `PATCH` | `/api/tasks/{id}` | Update task status, priority, or details | Yes |
| `POST` | `/api/tasks/{id}/breakdown` | AI generation of 3-5 micro-steps | Yes |
| `POST` | `/api/brain-dump` | Save raw brain dump text | Yes |
| `POST` | `/api/brain-dump/{id}/triage` | AI parsing of raw text into structured tasks | Yes |
| `GET` | `/api/routines` | Fetch user daily routines | Yes |
| `POST` | `/api/routines/{id}/complete` | Mark routine completed for today | Yes |
| `POST` | `/api/planning/generate` | AI generation of ADHD-optimised daily plan | Yes |
| `GET` | `/api/planning/today` | Fetch active daily plan for current date | Yes |
| `POST` | `/api/push/subscribe` | Register web push subscription keys | Yes |
| `POST` | `/api/push/send-test` | Dispatch test push notification | Yes |
| `POST` | `/api/mood` | Log mood and energy rating | Yes |
| `POST` | `/api/focus` | Record completed Pomodoro focus session | Yes |

---

## 5. Security & Authentication Architecture

1. **Token Ingestion**: The client attaches `Authorization: Bearer <supabase_access_token>` to REST calls.
2. **Dependency Gate (`app/dependencies.py`)**: `get_current_user` extracts credentials via `HTTPBearer`.
3. **Verification (`app/utils/auth.py`)**: Validates the JWT signature against `JWT_SECRET` or decodes Supabase payload to extract claims (`sub` = user UUID). Unauthenticated local testing falls back gracefully when configured.

---

## 6. AI Subsystem Integration (Google Gemini)

### 6.1 Engine & Configuration
- **Main Model**: Configured in `.env` via `GEMINI_MODEL_NAME` (no hardcoded code fallbacks).
- **Fallback Model**: Configured in `.env` via `GEMINI_BACKUP_MODEL_NAME` (no hardcoded code fallbacks).
- **Library**: `google.generativeai` initialized with `GEMINI_API_KEY`.

### 6.2 Prompt Engineering & Strict Output Schemas
1. **Daily Planner (`generate_gemini_daily_plan`)**:
   - Strictly limits focus tasks to max 3 per day.
   - Enforces 15-minute transition buffers and dual 30-minute flex blocks.
   - Restructures outputs into strict JSON containing `schedule`, `parked_tasks`, `daily_focus`, and `encouragement`.
2. **Task Breakdown (`breakdown_task_with_gemini`)**:
   - Deconstructs overwhelming tasks into 3 to 5 low-friction micro-steps.
   - Mandates the first step to be a tiny physical action (e.g. "Open laptop").
3. **Brain Dump Triage (`triage_brain_dump_with_gemini`)**:
   - Parses unstructured streams of consciousness into actionable tasks with estimated durations and energy requirement tags.

### 6.3 Resiliency & Fallback Mode
If `GEMINI_API_KEY` is omitted or API quotas fail, all AI helpers return structured fallback defaults (e.g., standard morning routine & focus block templates), ensuring zero backend downtime.

---

## 7. Push Notification Subsystem (VAPID / WebPush) — [DISABLED / COMMENTED OUT]

> [!NOTE]
> All code for the WebPush VAPID notification engine in `app/services/push_service.py`, `app/api/push.py`, and `app/scheduler/daily_planner.py` has been commented out for now.

1. **Protocol Standards (Inactive)**: Standard Web Push RFC 8030 using VAPID keys (`VAPID_PRIVATE_KEY`, `VAPID_PUBLIC_KEY`).
2. **Delivery Mechanism (`app/services/push_service.py`)**:
   - `send_push_notification()` currently returns `False` immediately.
   - Subscription endpoints in `app/api/push.py` are commented out.

---

## 8. Background Scheduler Subsystem (APScheduler)

- **Execution Engine**: `AsyncIOScheduler` managed inside FastAPI `lifespan` lifecycle.
- **Daily Planner Automation (`app/scheduler/daily_planner.py`)**:
  - Triggers every morning at 07:00 AM.
  - Queries active users, aggregates today's tasks & routines, generates Gemini daily plans automatically, and dispatches push notifications ("Your daily plan is ready!").

---

## 9. Error Handling & Deployment Strategy

- **Unified Exception Schema**: Standard `HTTPException` returns clear error payloads `{ "detail": "..." }`.
- **Environment Configuration**: Key secrets managed via `.env` / Render environment variables (`SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `GEMINI_API_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_PUBLIC_KEY`, `JWT_SECRET`).
- **Production Build**: FastAPI served via `uvicorn` / `gunicorn` workers (`uvicorn app.main:app --host 0.0.0.0 --port 8000`).
