-- Atomic, retry-safe queue claim for the Natasha background worker.
-- The function is SECURITY INVOKER: it relies on the worker's service_role
-- database connection (which bypasses RLS), not on SECURITY DEFINER.

create or replace function public.natasha_claim_jobs(p_limit integer default 1)
returns setof public.natasha_jobs
language sql
security invoker
set search_path = ''
as $$
  with candidates as (
    select j.id
    from public.natasha_jobs as j
    where (
      (j.status = 'queued' and j.run_at <= now())
      or
      (j.status = 'running' and j.locked_at < now() - interval '15 minutes')
    )
      and j.attempts < j.max_attempts
    order by j.run_at asc, j.created_at asc
    for update skip locked
    limit least(greatest(coalesce(p_limit, 1), 1), 10)
  )
  update public.natasha_jobs as j
  set status = 'running',
      locked_at = now(),
      attempts = j.attempts + 1,
      updated_at = now()
  from candidates
  where j.id = candidates.id
  returning j.*;
$$;

revoke all on function public.natasha_claim_jobs(integer) from public;
revoke all on function public.natasha_claim_jobs(integer) from anon;
revoke all on function public.natasha_claim_jobs(integer) from authenticated;
grant execute on function public.natasha_claim_jobs(integer) to service_role;
