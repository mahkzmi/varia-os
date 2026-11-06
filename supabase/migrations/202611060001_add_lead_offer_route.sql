-- Adds an explicit commercial route to each lead.
-- AI recommendations are provisional; founder review determines qualification.
alter table public.natasha_leads
  add column if not exists offer_route text not null default 'discovery_pending';

do $$
begin
  if not exists (
    select 1 from pg_constraint
    where conname = 'natasha_leads_offer_route_check'
      and conrelid = 'public.natasha_leads'::regclass
  ) then
    alter table public.natasha_leads
      add constraint natasha_leads_offer_route_check
      check (offer_route in ('audit', 'pilot', 'api_white_label', 'discovery_pending'));
  end if;
end $$;

comment on column public.natasha_leads.offer_route is
  'Provisional suggested commercial route for Varia Vision: audit, pilot, api_white_label, discovery_pending. AI suggestions are not buyer commitments.';
