-- Natasha hardening: stable RLS evaluation, function search_path, and FK indexes.

alter function public.natasha_set_updated_at() set search_path = '';

do $$
declare t text;
begin
  foreach t in array array[
    'natasha_companies',
    'natasha_contacts',
    'natasha_leads',
    'natasha_activities',
    'natasha_follow_ups',
    'natasha_message_drafts',
    'natasha_jobs',
    'natasha_audit_events'
  ]
  loop
    execute format('drop policy if exists %I on public.%I', t || '_owner_all', t);
    execute format(
      'create policy %I on public.%I for all using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id)',
      t || '_owner_all', t
    );
  end loop;
end $$;

create index if not exists natasha_companies_user_id_idx on public.natasha_companies(user_id);
create index if not exists natasha_contacts_user_id_idx on public.natasha_contacts(user_id);
create index if not exists natasha_contacts_company_id_idx on public.natasha_contacts(company_id);
create index if not exists natasha_leads_company_id_idx on public.natasha_leads(company_id);
create index if not exists natasha_leads_primary_contact_id_idx on public.natasha_leads(primary_contact_id);
create index if not exists natasha_activities_user_id_idx on public.natasha_activities(user_id);
create index if not exists natasha_activities_lead_id_idx on public.natasha_activities(lead_id);
create index if not exists natasha_activities_contact_id_idx on public.natasha_activities(contact_id);
create index if not exists natasha_follow_ups_lead_id_idx on public.natasha_follow_ups(lead_id);
create index if not exists natasha_message_drafts_user_id_idx on public.natasha_message_drafts(user_id);
create index if not exists natasha_message_drafts_lead_id_idx on public.natasha_message_drafts(lead_id);
create index if not exists natasha_jobs_user_id_idx on public.natasha_jobs(user_id);
create index if not exists natasha_audit_events_user_id_idx on public.natasha_audit_events(user_id);
