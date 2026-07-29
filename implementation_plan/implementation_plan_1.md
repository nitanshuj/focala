# Implementation Plan

-----

PWA + Supabase + FastAPI on Render + Gemini API is a solid, cost-effective stack that fits your requirements well. Here's a detailed breakdown of how to architect and build this.

## System Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                    CLIENT LAYER                      │
│                                                      │
│  ┌──────────────┐    ┌──────────────────────────┐   │
│  │   Web App     │    │   PWA (Chromebook/Win11) │   │
│  │  (React/Svelte)│   │   - Service Worker       │   │
│  │               │    │   - Push subscription    │   │
│  │               │    │   - Offline cache        │   │
│  └──────┬───────┘    └──────────┬───────────────┘   │
│         │       HTTPS API       │                    │
└─────────┼──────────────────────┼────────────────────┘
          │                      │
          ▼                      ▼
┌─────────────────────────────────────────────────────┐
│                  BACKEND LAYER (Render)              │
│                                                      │
│  ┌──────────────┐  ┌──────────┐  ┌───────────────┐ │
│  │   FastAPI    │  │  APScheduler│ │  Push Service  │ │
│  │  (REST API)  │  │  (Cron jobs)│ │  (web-push-py)│ │
│  │              │  │             │ │               │ │
│  │ - Task CRUD  │  │ - Daily     │ │ - VAPID keys  │ │
│  │ - Auth (JWT) │  │   planning  │ │ - Send pushes │ │
│  │ - Routines   │  │   trigger   │ │               │ │
│  └──────┬───────┘  └─────┬──────┘  └───────┬───────┘ │
│         │                │                  │         │
│         │    ┌───────────▼───────────┐     │         │
│         │    │   Gemini API Client    │     │         │
│         │    │   - Task breakdown     │     │         │
│         │    │   - Day scheduling     │     │         │
│         │    │   - Priority sorting   │     │         │
│         │    └────────────────────────┘     │         │
└─────────┼──────────────────────────────────┼─────────┘
          │                                  │
          ▼                                  ▼
┌─────────────────────────────────────────────────────┐
│               DATA LAYER (Supabase)                  │
│                                                      │
│  PostgreSQL | Auth | Realtime | Storage              │
│  - RLS policies for user isolation                   │
│  - Tables: users, tasks, routines,                  │
│    brain_dumps, push_subscriptions, settings         │
└─────────────────────────────────────────────────────┘
```

## PWA Setup & Push Notifications

PWA push notifications work natively on Windows 11 (via Chrome and Edge) and on Chromebook (Chrome OS has first-class PWA support). The key components are: [intercom](https://intercom.help/progressier/en/articles/5703031-which-devices-browsers-are-compatible-with-web-push-notifications)

- **Service Worker** (`sw.js`) — Registers in the browser, listens for `push` events, and displays notifications using `self.registration.showNotification()`. Also handles `notificationclick` to open/focus the app [learningtree](https://www.learningtree.com/blog/utilizing-push-notifications-progressive-web-app-pwa/)
- **Web Push subscription** — On first launch, the PWA requests notification permission, then subscribes via `pushManager.subscribe()` with your VAPID public key. The subscription endpoint + keys are sent to your backend and stored in Supabase [github](https://github.com/Frac7/PWAShifts)
- **VAPID key pair** — Generate once using `web-push` (npm) or `pywebpush` (Python). The public key goes in the frontend; the private key stays on the server [learningtree](https://www.learningtree.com/blog/utilizing-push-notifications-progressive-web-app-pwa/)
- **Backend push sender** — Use the `pywebpush` Python library on Render to send push messages to stored subscription objects. No Firebase/FCM needed — direct web push protocol [habr](https://habr.com/ru/articles/945870/)

### Critical Windows 11 Gotcha

For push notifications to fire when the PWA isn't actively open, the browser (Chrome or Edge) must be running in the background. Two settings are essential: [3cx](https://www.3cx.com/blog/docs/pwa-push-notifications/)

- Enable **"Start app when you sign in"** on the installed PWA (right-click → App info → Settings)
- Enable **"Continue running background apps when browser is closed"** (Chrome: Settings → System; Edge: Settings → System and Performance)

If the user fully quits the browser, push notifications will stop until it reopens. You should surface this as a one-time onboarding tip in your app.



## Python Backend (FastAPI on Render)

### Recommended Stack

| Component | Tool | Purpose |
|-----------|------|---------|
| Web framework | FastAPI | REST API, auto-docs, async support |
| ORM | Supabase Python client or SQLAlchemy | DB access  [supabase](https://supabase.com/docs/guides/getting-started/quickstarts/flask) |
| Scheduler | APScheduler | Cron-based daily planning triggers |
| Push sender | `pywebpush` | Send web push notifications  [habr](https://habr.com/ru/articles/945870/) |
| Gemini client | `google-generativeai` | LLM calls for task planning  [ai.google](https://ai.google.dev/competition/projects/task-manager) |
| Deployment | Render (Web Service) | Hosts FastAPI app  [stackcompat](https://www.stackcompat.dev/render-with-supabase/) |
| Background jobs | Render Cron Job OR APScheduler in-app | Daily planning at user's preferred time |

### Key API Endpoints

```
# Auth (delegated to Supabase Auth, JWT verified in FastAPI)
POST   /api/auth/verify          # Verify Supabase JWT

# Tasks
GET    /api/tasks                # List tasks (filter by status, date, energy)
POST   /api/tasks                # Create task
PATCH  /api/tasks/{id}           # Update status, time, etc.
DELETE /api/tasks/{id}
POST   /api/tasks/{id}/breakdown # Gemini breaks task into micro-steps

# Brain Dump
GET    /api/brain-dumps
POST   /api/brain-dumps          # Quick capture
POST   /api/brain-dumps/{id}/triage  # Convert to task(s)

# Daily Planning (Gemini-powered)
POST   /api/plan/generate        # Trigger Gemini to create today's schedule
GET    /api/plan/today            # Fetch today's plan
POST   /api/plan/rebalance       # Mid-day replan if tasks slip

# Routines
GET    /api/routines
POST   /api/routines
POST   /api/routines/{id}/complete  # Mark routine steps done

# Push Notifications
POST   /api/push/subscribe       # Store push subscription from PWA
POST   /api/push/unsubscribe
POST   /api/push/test            # Send test notification

# Mood & Reflection
POST   /api/mood                 # Quick energy/mood check-in
GET    /api/mood/trends          # Weekly patterns
```

### Gemini Integration for Daily Planning

The Gemini API excels at task scheduling — it can analyze all pending tasks, their urgency, estimated time, user's energy pattern, and generate an optimized time-blocked schedule. Here's the flow: [ai.google](https://ai.google.dev/competition/projects/task-manager)

```python
import google.generativeai as genai
from datetime import datetime, date
import json

genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-2.0-flash')

DAILY_PLANNER_PROMPT = """
You are an ADHD-friendly daily planner. Given the user's tasks, energy pattern,
and available time blocks, create an optimized schedule.

ADHD PRINCIPLES TO FOLLOW:
1. Never schedule more than 3 high-priority tasks per day
2. Break large tasks into micro-steps (first physical action)
3. Place high-energy tasks during peak energy windows
4. Include 15-min transition buffers between blocks
5. Add 2 "flex blocks" (30 min each) for overflow/meltdown recovery
6. If tasks exceed available time, park the lowest-priority ones (don't overload)
7. Tone: encouraging, not guilt-inducing

Return JSON only:
{
  "schedule": [
    {
      "time_block": "09:00-09:25",
      "task_title": "...",
      "task_id": "...",
      "micro_step": "First action: ...",
      "energy_required": "high",
      "type": "focus" | "break" | "transition" | "routine" | "flex"
    }
  ],
  "parked_tasks": ["task_id", ...],
  "daily_focus": "One sentence: what matters most today",
  "encouragement": "Short ADHD-friendly motivational note"
}
"""

async def generate_daily_plan(user_id: str, plan_date: date):
    # Fetch pending tasks, routines, mood history from Supabase
    tasks = await supabase.from_("tasks").select("*").eq(
        "user_id", user_id
    ).eq("status", "pending").execute()
    
    routines = await supabase.from_("routines").select("*").eq(
        "user_id", user_id
    ).eq("active", True).execute()
    
    profile = await supabase.from_("profiles").select("*").eq(
        "id", user_id
    ).single().execute()
    
    context = {
        "tasks": tasks.data,
        "routines": routines.data,
        "energy_pattern": profile.data.get("energy_pattern"),
        "available_hours": "09:00-21:00",  # Could be user-configurable
        "date": str(plan_date),
    }
    
    response = model.generate_content(
        f"{DAILY_PLANNER_PROMPT}\n\nUser data:\n{json.dumps(context, default=str)}"
    )
    
    plan = json.loads(response.text)
    
    # Store plan in Supabase
    await supabase.from_("daily_plans").upsert({
        "user_id": user_id,
        "plan_date": str(plan_date),
        "schedule": plan,
        "raw_gemini_response": response.text
    }).execute()
    
    # Send "Your plan is ready" push notification
    await send_push_notification(
        user_id, 
        title="📅 Your day is planned",
        body=plan.get("daily_focus", "Tap to see your schedule"),
        url="/today"
    )
    
    return plan
```

### Scheduler (APScheduler in FastAPI)

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job(CronTrigger(hour=7, minute=0))  # 7 AM daily
async def daily_planning_job():
    # Fetch all users with gemini_enabled = true
    users = await supabase.from_("profiles").select(
        "id"
    ).eq("gemini_enabled", True).execute()
    
    for user in users.data:
        try:
            await generate_daily_plan(user["id"], date.today())
        except Exception as e:
            print(f"Planning failed for {user['id']}: {e}")

# Transition reminder (sends push 5 min before each scheduled block)
@scheduler.scheduled_job(CronTrigger(minute="*/5"))  # Check every 5 min
async def transition_reminders():
    now = datetime.utcnow()
    # Query upcoming time blocks from daily_plans
    # Send push: "Starting in 5 min: [task name] — First step: [micro_step]"
    ...

# Streak preservation (evening check-in)
@scheduler.scheduled_job(CronTrigger(hour=20, minute=0))
async def evening_checkin():
    # Send gentle push: "Quick check-in? How was your energy today?"
    ...

scheduler.start()
```

### Push Notification Sender

```python
from pywebpush import webpush, WebPushException
import json

VAPID_PRIVATE_KEY = os.environ["VAPID_PRIVATE_KEY"]
VAPID_CLAIMS = {"sub": "mailto:admin@yourapp.com"}

async def send_push_notification(user_id: str, title: str, body: str, url: str = "/"):
    subs = await supabase.from_("push_subscriptions").select("*").eq(
        "user_id", user_id
    ).execute()
    
    for sub in subs.data:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub["endpoint"],
                    "keys": sub["keys"],
                },
                data=json.dumps({
                    "title": title,
                    "body": body,
                    "url": url,
                    "timestamp": int(datetime.now().timestamp())
                }),
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims=VAPID_CLAIMS,
            )
        except WebPushException as e:
            if e.response and e.response.status_code == 410:
                # Subscription expired, delete it
                await supabase.from_("push_subscriptions").delete().eq(
                    "id", sub["id"]
                ).execute()
            print(f"Push failed: {e}")
```

## PWA Frontend Configuration

### manifest.json

```json
{
  "name": "FocusFlow — ADHD Planner",
  "short_name": "FocusFlow",
  "description": "Your ADHD-friendly daily planner and organizer",
  "start_url": "/today",
  "display": "standalone",
  "background_color": "#0f172a",
  "theme_color": "#6366f1",
  "orientation": "any",
  "icons": [
    {
      "src": "/icons/icon-192.png",
      "sizes": "192x192",
      "type": "image/png",
      "purpose": "any maskable"
    },
    {
      "src": "/icons/icon-512.png",
      "sizes": "512x512",
      "type": "image/png",
      "purpose": "any maskable"
    }
  ],
  "shortcuts": [
    {
      "name": "Brain Dump",
      "url": "/brain-dump",
      "icons": [{"src": "/icons/brain-96.png", "sizes": "96x96"}]
    },
    {
      "name": "Today's Plan",
      "url": "/today",
      "icons": [{"src": "/icons/today-96.png", "sizes": "96x96"}]
    }
  ]
}
```

### Service Worker (Push Handler)

```javascript
// sw.js
self.addEventListener('install', (event) => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener('push', (event) => {
  const data = event.data.json();
  const options = {
    body: data.body,
    icon: '/icons/icon-192.png',
    badge: '/icons/badge-72.png',
    vibrate: [100, 50, 100],
    tag: data.tag || 'default',
    data: { url: data.url || '/today' },
    actions: [
      { action: 'open', title: 'Open' },
      { action: 'snooze', title: 'Snooze 10 min' }
    ]
  };
  event.waitUntil(
    self.registration.showNotification(data.title, options)
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  if (event.action === 'snooze') {
    // Send API call to reschedule reminder
    fetch('/api/push/snooze', { method: 'POST', body: JSON.stringify({tag: event.notification.tag}) });
  } else {
    event.waitUntil(
      clients.openWindow(event.notification.data.url)
    );
  }
});
```

## Render Deployment Setup

### `render.yaml` (Infrastructure as Code)

```yaml
services:
  - type: web
    name: focusflow-api
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT
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
    plan: starter  # $7/mo, sufficient for dev

  - type: cron
    name: daily-planner
    runtime: python
    schedule: "0 1 * * *"  # 1 AM UTC = ~6:30 AM IST
    buildCommand: pip install -r requirements.txt
    startCommand: python -m scheduler.daily_planning
    envVars:
      # Same env vars as above
```

Render supports both web services (always-on FastAPI) and background workers/cron jobs, and integrates seamlessly with Supabase via environment variables. [stackcompat](https://www.stackcompat.dev/render-with-supabase/)

## Recommended Frontend Stack

| Layer | Recommendation | Why |
|-------|---------------|-----|
| Framework | React + Vite or SvelteKit | Fast, large ecosystem, PWA plugins available |
| PWA tooling | `vite-plugin-pwa` | Auto-generates service worker, manifest, handles updates |
| Styling | Tailwind CSS | Utility-first, low cognitive load to maintain, great for visual ADHD-friendly design |
| State | Zustand or TanStack Query | Lightweight, TanStack Query handles Supabase caching/sync |
| Supabase client | `@supabase/supabase-js` | Direct frontend DB access with RLS for real-time updates |
| UI components | shadcn/ui or DaisyUI | Accessible, customizable, can implement ADHD-friendly patterns (low clutter, high contrast) |

## Key Implementation Tips

- **Supabase RLS is your security backbone** — The frontend can talk directly to Supabase for CRUD operations (tasks, brain dumps, routines) using the anon key + user JWT, while FastAPI handles only the Gemini-powered and push notification logic. This reduces backend load significantly [stackcompat](https://www.stackcompat.dev/render-with-supabase/)
- **Gemini calls should be idempotent** — If the daily plan generation fails or times out, the scheduler should retry without creating duplicate plans (use the `unique(user_id, plan_date)` constraint)
- **Push subscription cleanup** — Expired/410-gone subscriptions must be deleted from the DB, otherwise every push attempt will throw errors [habr](https://habr.com/ru/articles/945870/)
- **Rate-limit Gemini calls** — Gemini has per-minute request limits; if you batch-plan for many users at 7 AM, stagger them (e.g., process 5 users, sleep 10s, next 5)
- **Offline support** — Cache the daily plan in the service worker so the user can view their schedule even when offline; queue task completions and sync when back online
- **Gemini model choice** — Use `gemini-2.0-flash` for daily planning (fast, cheap) and reserve `gemini-2.5-pro` for complex task breakdown if needed [ai.google](https://ai.google.dev/competition/projects/task-manager)

## Development Order

1. Set up Supabase project, auth, and schema with RLS
2. Build FastAPI skeleton + Supabase connection on Render
3. Implement task CRUD (frontend talks to Supabase directly)
4. Add Gemini daily planning endpoint + scheduler
5. Implement PWA manifest + service worker
6. Add push subscription flow + `pywebpush` sender
7. Build the frontend UI with ADHD-friendly design principles
8. Add brain dump, routines, mood tracking features
9. Test push notifications on Chromebook and Windows 11