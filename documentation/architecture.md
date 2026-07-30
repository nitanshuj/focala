# System Architecture Overview

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