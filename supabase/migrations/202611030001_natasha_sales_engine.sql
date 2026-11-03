-- Natasha sales engine: isolated, user-owned tables.
-- Apply with Supabase SQL editor or Supabase CLI after reviewing the project schema.

create extension if not exists pgcrypto;

create table if not exists public.natasha_companies (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  name text not null,
  website text,
  industry text,
  country text,
  notes text,
  source text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.natasha_contacts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  company_id uuid references public.natasha_companies(id) on delete set null,
  full_name text not null,
  role text,
  email text,
  linkedin_url text,
  is_decision_maker boolean not null default false,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.natasha_leads (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  company_id uuid references public.natasha_companies(id) on delete set null,
  primary_contact_id uuid references public.natasha_contacts(id) on delete set null,
  product text not null check (product in ('Varia Carbon','Varia Vision','Varia Trait-Bridge','Other')),
  stage text not null default 'new' check (stage in ('new','researching','qualified','contacted','replied','meeting','proposal','pilot','won','disqualified','lost')),
  source text,
  fit_score smallint check (fit_score between 0 and 100),
  fit_rationale text,
  estimated_value numeric(12,2),
  currency char(3) not null default 'USD',
  next_action text,
  next_action_at timestamptz,
  last_contacted_at timestamptz,
  lost_reason text,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.natasha_activities (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  lead_id uuid references public.natasha_leads(id) on delete cascade,
  contact_id uuid references public.natasha_contacts(id) on delete set null,
  activity_type text not null check (activity_type in ('note','research','email_draft','email_sent','reply','call','meeting','stage_change','follow_up')),
  subject text,
  body text,
  occurred_at timestamptz not null default now(),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.natasha_follow_ups (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  lead_id uuid not null references public.natasha_leads(id) on delete cascade,
  title text not null,
  due_at timestamptz not null,
  status text not null default 'pending' check (status in ('pending','snoozed','completed','cancelled')),
  snoozed_until timestamptz,
  completed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.natasha_message_drafts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  lead_id uuid references public.natasha_leads(id) on delete cascade,
  channel text not null default 'email' check (channel in ('email')),
  recipient text not null,
  subject text not null,
  body text not null,
  status text not null default 'draft' check (status in ('draft','approved','sent','rejected')),
  approved_at timestamptz,
  sent_at timestamptz,
  provider_message_id text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.natasha_jobs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  job_type text not null,
  payload jsonb not null default '{}'::jsonb,
  idempotency_key text not null,
  run_at timestamptz not null default now(),
  status text not null default 'queued' check (status in ('queued','running','succeeded','failed','cancelled')),
  attempts integer not null default 0,
  max_attempts integer not null default 5,
  locked_at timestamptz,
  last_error text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, idempotency_key)
);

create table if not exists public.natasha_audit_events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  entity_type text not null,
  entity_id uuid,
  action text not null,
  details jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists natasha_leads_user_stage_idx on public.natasha_leads(user_id, stage);
create index if not exists natasha_leads_followup_idx on public.natasha_leads(user_id, next_action_at);
create index if not exists natasha_followups_due_idx on public.natasha_follow_ups(user_id, due_at) where status in ('pending','snoozed');
create index if not exists natasha_jobs_due_idx on public.natasha_jobs(run_at) where status = 'queued';
create index if not exists natasha_activities_lead_time_idx on public.natasha_activities(lead_id, occurred_at desc);

create or replace function public.natasha_set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

do $$
declare t text;
begin
  foreach t in array array['natasha_companies','natasha_contacts','natasha_leads','natasha_follow_ups','natasha_message_drafts','natasha_jobs']
  loop
    execute format('drop trigger if exists %I on public.%I', t || '_updated_at', t);
    execute format('create trigger %I before update on public.%I for each row execute function public.natasha_set_updated_at()', t || '_updated_at', t);
  end loop;
end $$;

alter table public.natasha_companies enable row level security;
alter table public.natasha_contacts enable row level security;
alter table public.natasha_leads enable row level security;
alter table public.natasha_activities enable row level security;
alter table public.natasha_follow_ups enable row level security;
alter table public.natasha_message_drafts enable row level security;
alter table public.natasha_jobs enable row level security;
alter table public.natasha_audit_events enable row level security;

do $$
declare t text;
begin
  foreach t in array array['natasha_companies','natasha_contacts','natasha_leads','natasha_activities','natasha_follow_ups','natasha_message_drafts','natasha_jobs','natasha_audit_events']
  loop
    execute format('drop policy if exists %I on public.%I', t || '_owner_all', t);
    execute format('create policy %I on public.%I for all using (auth.uid() = user_id) with check (auth.uid() = user_id)', t || '_owner_all', t);
  end loop;
end $$;
