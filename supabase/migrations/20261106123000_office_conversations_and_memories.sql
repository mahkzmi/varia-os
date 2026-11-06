-- Durable chat history and agent-scoped memory for Varia Studio HQ.
create table if not exists public.office_conversations (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  agent text not null check (agent in ('natasha','marketing','operations')),
  title text not null default 'New conversation',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists office_conversations_user_updated_idx on public.office_conversations(user_id, updated_at desc);
create table if not exists public.office_messages (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references public.office_conversations(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  agent text not null check (agent in ('natasha','marketing','operations')),
  role text not null check (role in ('founder','agent','system')),
  content text not null check (length(content) between 1 and 20000),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists office_messages_conversation_created_idx on public.office_messages(conversation_id, created_at asc);
create index if not exists office_messages_user_created_idx on public.office_messages(user_id, created_at desc);
create table if not exists public.office_agent_memories (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  agent text not null check (agent in ('natasha','marketing','operations','shared')),
  memory_type text not null default 'founder_note' check (memory_type in ('founder_note','preference','decision','project_context','lesson')),
  content text not null check (length(content) between 1 and 5000),
  importance smallint not null default 3 check (importance between 1 and 5),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists office_agent_memories_user_agent_idx on public.office_agent_memories(user_id, agent, importance desc, updated_at desc);
alter table public.office_conversations enable row level security;
alter table public.office_messages enable row level security;
alter table public.office_agent_memories enable row level security;
grant select, insert, update, delete on public.office_conversations to authenticated;
grant select, insert, update, delete on public.office_messages to authenticated;
grant select, insert, update, delete on public.office_agent_memories to authenticated;
drop policy if exists office_conversations_owner_all on public.office_conversations;
create policy office_conversations_owner_all on public.office_conversations for all to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
drop policy if exists office_messages_owner_all on public.office_messages;
create policy office_messages_owner_all on public.office_messages for all to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id and exists (select 1 from public.office_conversations c where c.id = conversation_id and c.user_id = (select auth.uid())));
drop policy if exists office_agent_memories_owner_all on public.office_agent_memories;
create policy office_agent_memories_owner_all on public.office_agent_memories for all to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
