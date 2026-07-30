# Supabase Postgres Database Schema & Migration SQL

---

## Complete SQL Migration Script

```sql
-- Enable necessary extensions
create extension if not exists "uuid-ossp";

--------------------------------------------------------------------------------
-- 1. PROFILES TABLE (Extends Supabase Auth users)
--------------------------------------------------------------------------------
create table if not exists public.profiles (
  id uuid references auth.users on delete cascade primary key,
  display_name text,
  energy_pattern text default 'flexible',  -- morning_person, night_owl, flexible
  notification_prefs jsonb default '{"reminders": true, "streak_alerts": true, "transition_warnings": true}',
  gemini_enabled boolean default true,
  created_at timestamptz default now()
);

-- Trigger to automatically create a profile entry when a user signs up
create or replace function public.handle_new_user()
returns trigger as $$
begin
  insert into public.profiles (id, display_name)
  values (new.id, coalesce(new.raw_user_meta_data->>'full_name', new.email));
  return new;
end;
$$ language plpgsql security definer;

-- Drop trigger if exists and recreate
drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();


--------------------------------------------------------------------------------
-- 2. TASKS TABLE (Tasks, micro-steps & scheduling)
--------------------------------------------------------------------------------
create table if not exists public.tasks (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users on delete cascade not null,
  title text not null,
  description text,
  status text default 'pending',       -- pending, in_progress, done, parked
  priority text default 'medium',      -- low, medium, high, urgent
  energy_level text default 'medium',  -- low, medium, high
  estimated_minutes int default 30,
  actual_minutes int,
  scheduled_start timestamptz,
  scheduled_end timestamptz,
  parent_task_id uuid references public.tasks(id) on delete cascade,  -- micro-step relation
  is_micro_step boolean default false,
  ai_generated boolean default false,
  completed_at timestamptz,
  rolled_over_count int default 0,
  created_at timestamptz default now()
);

create index if not exists idx_tasks_user_status on public.tasks(user_id, status);
create index if not exists idx_tasks_parent_id on public.tasks(parent_task_id);


--------------------------------------------------------------------------------
-- 3. BRAIN DUMPS TABLE (Unstructured quick-capture inbox)
--------------------------------------------------------------------------------
create table if not exists public.brain_dumps (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users on delete cascade not null,
  content text not null,
  triaged boolean default false,
  converted_task_id uuid references public.tasks(id) on delete set null,
  created_at timestamptz default now()
);

create index if not exists idx_brain_dumps_user_triaged on public.brain_dumps(user_id, triaged);


--------------------------------------------------------------------------------
-- 4. ROUTINES TABLE (Habit templates)
--------------------------------------------------------------------------------
create table if not exists public.routines (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users on delete cascade not null,
  name text not null,
  trigger_time time,
  active boolean default true,
  steps jsonb not null default '[]',  -- [{label, icon, est_minutes}]
  created_at timestamptz default now()
);

create index if not exists idx_routines_user_active on public.routines(user_id, active);


--------------------------------------------------------------------------------
-- 5. ROUTINE COMPLETIONS TABLE (Habit streak logging)
--------------------------------------------------------------------------------
create table if not exists public.routine_completions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users on delete cascade not null,
  routine_id uuid references public.routines(id) on delete cascade not null,
  completed_steps jsonb default '[]',
  completed_at date not null default current_date,
  constraint unique_user_routine_completion unique(user_id, routine_id, completed_at)
);

create index if not exists idx_routine_completions_user_date on public.routine_completions(user_id, completed_at);


--------------------------------------------------------------------------------
-- 6. PUSH SUBSCRIPTIONS TABLE (Web Push Notification Tokens)
--------------------------------------------------------------------------------
create table if not exists public.push_subscriptions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users on delete cascade not null,
  endpoint text not null,
  keys jsonb not null,  -- {p256dh, auth}
  user_agent text,
  created_at timestamptz default now(),
  constraint unique_user_endpoint unique(user_id, endpoint)
);

create index if not exists idx_push_subscriptions_user on public.push_subscriptions(user_id);


--------------------------------------------------------------------------------
-- 7. DAILY PLANS TABLE (Gemini-generated AI Schedules)
--------------------------------------------------------------------------------
create table if not exists public.daily_plans (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users on delete cascade not null,
  plan_date date not null,
  schedule jsonb not null,
  raw_gemini_response text,
  created_at timestamptz default now(),
  constraint unique_user_plan_date unique(user_id, plan_date)
);

create index if not exists idx_daily_plans_user_date on public.daily_plans(user_id, plan_date);


--------------------------------------------------------------------------------
-- 8. MOOD LOGS TABLE (Energy & Mood Check-ins)
--------------------------------------------------------------------------------
create table if not exists public.mood_logs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users on delete cascade not null,
  energy_level int check (energy_level between 1 and 5) not null,
  mood text,
  note text,
  logged_at timestamptz default now()
);

create index if not exists idx_mood_logs_user_logged on public.mood_logs(user_id, logged_at);


--------------------------------------------------------------------------------
-- ROW LEVEL SECURITY (RLS) POLICIES
--------------------------------------------------------------------------------

-- Enable RLS on all tables
alter table public.profiles enable row level security;
alter table public.tasks enable row level security;
alter table public.brain_dumps enable row level security;
alter table public.routines enable row level security;
alter table public.routine_completions enable row level security;
alter table public.push_subscriptions enable row level security;
alter table public.daily_plans enable row level security;
alter table public.mood_logs enable row level security;

-- PROFILES RLS
create policy "Users can view own profile" on public.profiles
  for select using (auth.uid() = id);
create policy "Users can update own profile" on public.profiles
  for update using (auth.uid() = id);

-- TASKS RLS
create policy "Users can view own tasks" on public.tasks
  for select using (auth.uid() = user_id);
create policy "Users can insert own tasks" on public.tasks
  for insert with check (auth.uid() = user_id);
create policy "Users can update own tasks" on public.tasks
  for update using (auth.uid() = user_id);
create policy "Users can delete own tasks" on public.tasks
  for delete using (auth.uid() = user_id);

-- BRAIN DUMPS RLS
create policy "Users can view own brain dumps" on public.brain_dumps
  for select using (auth.uid() = user_id);
create policy "Users can insert own brain dumps" on public.brain_dumps
  for insert with check (auth.uid() = user_id);
create policy "Users can update own brain dumps" on public.brain_dumps
  for update using (auth.uid() = user_id);
create policy "Users can delete own brain dumps" on public.brain_dumps
  for delete using (auth.uid() = user_id);

-- ROUTINES RLS
create policy "Users can view own routines" on public.routines
  for select using (auth.uid() = user_id);
create policy "Users can insert own routines" on public.routines
  for insert with check (auth.uid() = user_id);
create policy "Users can update own routines" on public.routines
  for update using (auth.uid() = user_id);
create policy "Users can delete own routines" on public.routines
  for delete using (auth.uid() = user_id);

-- ROUTINE COMPLETIONS RLS
create policy "Users can view own routine completions" on public.routine_completions
  for select using (auth.uid() = user_id);
create policy "Users can insert own routine completions" on public.routine_completions
  for insert with check (auth.uid() = user_id);
create policy "Users can update own routine completions" on public.routine_completions
  for update using (auth.uid() = user_id);

-- PUSH SUBSCRIPTIONS RLS
create policy "Users can view own push subscriptions" on public.push_subscriptions
  for select using (auth.uid() = user_id);
create policy "Users can insert own push subscriptions" on public.push_subscriptions
  for insert with check (auth.uid() = user_id);
create policy "Users can update own push subscriptions" on public.push_subscriptions
  for update using (auth.uid() = user_id);
create policy "Users can delete own push subscriptions" on public.push_subscriptions
  for delete using (auth.uid() = user_id);

-- DAILY PLANS RLS
create policy "Users can view own daily plans" on public.daily_plans
  for select using (auth.uid() = user_id);
create policy "Users can insert own daily plans" on public.daily_plans
  for insert with check (auth.uid() = user_id);
create policy "Users can update own daily plans" on public.daily_plans
  for update using (auth.uid() = user_id);

-- MOOD LOGS RLS
create policy "Users can view own mood logs" on public.mood_logs
  for select using (auth.uid() = user_id);
create policy "Users can insert own mood logs" on public.mood_logs
  for insert with check (auth.uid() = user_id);
create policy "Users can update own mood logs" on public.mood_logs
  for update using (auth.uid() = user_id);
create policy "Users can delete own mood logs" on public.mood_logs
  for delete using (auth.uid() = user_id);

--------------------------------------------------------------------------------
-- 9. CALENDAR_CONNECTIONS TABLE (Google Calendar OAuth tokens)
--------------------------------------------------------------------------------
create table if not exists public.calendar_connections (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade unique not null,
  google_email text not null,
  access_token text not null,
  refresh_token text not null,
  token_expiry timestamptz not null,
  connected_at timestamptz default now()
);

-- CALENDAR CONNECTIONS RLS
alter table public.calendar_connections enable row level security;
create policy "Users manage own calendar connection" on public.calendar_connections
  for all using (auth.uid() = user_id);
```