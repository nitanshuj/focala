## Supabase Schema Design

Here's a recommended schema optimized for ADHD planner features:

```sql
-- Users & settings (Supabase Auth handles users table)
create table public.profiles (
  id uuid references auth.users primary key,
  display_name text,
  energy_pattern text default 'flexible',  -- morning_person, night_owl, flexible
  notification_prefs jsonb default '{"reminders": true, "streak_alerts": true, "transition_warnings": true}',
  gemini_enabled boolean default true,
  created_at timestamptz default now()
);

-- Tasks
create table public.tasks (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users on delete cascade,
  title text not null,
  description text,
  status text default 'pending',  -- pending, in_progress, done, parked
  priority text default 'medium',  -- low, medium, high, urgent
  energy_level text,  -- low, medium, high
  estimated_minutes int,
  actual_minutes int,
  scheduled_start timestamptz,
  scheduled_end timestamptz,
  parent_task_id uuid references public.tasks(id),  -- for micro-steps
  is_micro_step boolean default false,
  ai_generated boolean default false,
  completed_at timestamptz,
  rolled_over_count int default 0,
  created_at timestamptz default now()
);

-- Brain dump inbox
create table public.brain_dumps (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users on delete cascade,
  content text not null,
  triaged boolean default false,
  converted_task_id uuid references public.tasks(id),
  created_at timestamptz default now()
);

-- Routines (templates)
create table public.routines (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users on delete cascade,
  name text not null,  -- "Morning Routine", "Evening Wind-down"
  trigger_time time,
  active boolean default true,
  steps jsonb not null default '[]',  -- [{label, icon, est_minutes}]
  created_at timestamptz default now()
);

-- Routine completions (for streaks)
create table public.routine_completions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users on delete cascade,
  routine_id uuid references public.routines on delete cascade,
  completed_steps jsonb default '[]',
  completed_at date not null,
  unique(user_id, routine_id, completed_at)
);

-- Push subscriptions
create table public.push_subscriptions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users on delete cascade,
  endpoint text not null,
  keys jsonb not null,  -- {p256dh, auth}
  user_agent text,
  created_at timestamptz default now()
);

-- Daily AI plans
create table public.daily_plans (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users on delete cascade,
  plan_date date not null,
  schedule jsonb not null,  -- structured Gemini output
  raw_gemini_response text,
  created_at timestamptz default now(),
  unique(user_id, plan_date)
);

-- Mood/energy logs
create table public.mood_logs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users on delete cascade,
  energy_level int check (energy_level between 1 and 5),
  mood text,
  note text,
  logged_at timestamptz default now()
);

-- Row Level Security
alter table public.tasks enable row level security;
create policy "Users see own tasks" on public.tasks
  for select using (auth.uid() = user_id);
create policy "Users modify own tasks" on public.tasks
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- Repeat RLS for all tables with user_id...
```