# API Endpoints Specification

All API endpoints are prefixed with `/api` and require a valid Bearer Token in the HTTP Header:
`Authorization: Bearer <SUPABASE_JWT_TOKEN>`

---

## 1. Tasks & Micro-Steps (`/api/tasks`)

| Method | Endpoint | Description | Request Body / Query | Response |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/tasks` | List user tasks | `?status=pending\|done\|parked` | `List[TaskResponse]` |
| `POST` | `/api/tasks` | Create a new task | `TaskCreate` | `TaskResponse` |
| `PATCH` | `/api/tasks/{task_id}` | Update task details/status | `TaskUpdate` | `TaskResponse` |
| `DELETE` | `/api/tasks/{task_id}` | Delete a task | None | `204 No Content` |
| `POST` | `/api/tasks/{task_id}/breakdown` | Gemini micro-step task decomposition | None | `TaskBreakdownResponse` |
| `POST` | `/api/tasks/rollover` | Auto-rollover pending past tasks to today | None | `{ message, rolled_over_count, tasks }` |
| `GET` | `/api/tasks/summary/today` | Fetch reverse to-do list & dopamine stats | None | `TaskSummaryResponse` |

---

## 2. Brain Dump Inbox (`/api/brain-dumps`)

| Method | Endpoint | Description | Request Body / Query | Response |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/brain-dumps` | List raw brain dump entries | None | `List[BrainDumpResponse]` |
| `POST` | `/api/brain-dumps` | Quick capture thought entry | `BrainDumpCreate` | `BrainDumpResponse` |
| `POST` | `/api/brain-dumps/{dump_id}/triage` | AI triage thought into tasks via Gemini | None | `{ message, created_tasks_count, tasks }` |

---

## 3. AI Daily Planning (`/api/plan`)

| Method | Endpoint | Description | Request Body / Query | Response |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/plan/generate` | Generate AI daily time-blocked schedule | `GeneratePlanRequest` | `DailyPlanResponse` |
| `GET` | `/api/plan/today` | Retrieve today's active schedule | None | `{ plan_date, schedule, message }` |
| `POST` | `/api/plan/rebalance` | Mid-day schedule rebalancing | `RebalancePlanRequest` | `DailyPlanResponse` |

---

## 4. Focus & Body Doubling (`/api/focus`)

| Method | Endpoint | Description | Request Body / Query | Response |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/focus/session` | Log completed focus session & award win | `FocusSessionLog` | `FocusSessionResponse` |
| `GET` | `/api/focus/rooms` | Fetch ambient body doubling rooms | None | `{ active_rooms: [...] }` |

---

## 5. Routines & Habit Checklist (`/api/routines`)

| Method | Endpoint | Description | Request Body / Query | Response |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/routines` | List active user routines | None | `List[RoutineResponse]` |
| `POST` | `/api/routines` | Create routine checklist | `RoutineCreate` | `RoutineResponse` |
| `PATCH` | `/api/routines/{routine_id}` | Update routine settings | `RoutineUpdate` | `RoutineResponse` |
| `POST` | `/api/routines/{routine_id}/complete` | Mark routine step(s) completed | `RoutineCompletionRequest` | `RoutineCompletionResponse` |

---

## 6. Energy & Mood Analytics (`/api/mood`)

| Method | Endpoint | Description | Request Body / Query | Response |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/mood` | Log mood & energy level check-in | `MoodLogCreate` | `MoodLogResponse` |
| `GET` | `/api/mood/trends` | Fetch 30-day energy trends summary | None | `EnergyTrendSummary` |

---

## 7. Web Push Notifications (`/api/push`)

| Method | Endpoint | Description | Request Body / Query | Response |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/push/subscribe` | Register PWA push subscription | `PushSubscribeRequest` | `PushSubscribeResponse` |
| `POST` | `/api/push/unsubscribe` | Delete push subscription endpoint | `?endpoint=<string>` | `{ status: "unsubscribed" }` |
| `POST` | `/api/push/test` | Send test push notification | `PushTestNotification` | `{ status, detail }` |

---

## 8. Calendar Synchronization (`/api/calendar`)

| Method | Endpoint | Description | Request Body / Query | Response |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/calendar/events` | Sync & fetch Google Calendar events | None | `CalendarSyncResponse` |
