-- Harden queue-claim RPCs and recover abandoned worker leases.
-- Applied to the Varia OS Supabase project on 2026-11-06.

CREATE OR REPLACE FUNCTION public.office_claim_tasks(p_limit integer DEFAULT 1)
RETURNS SETOF public.office_tasks
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path TO ''
AS $function$
BEGIN
  UPDATE public.office_tasks
  SET status = 'failed',
      locked_at = NULL,
      error = COALESCE(error, 'Worker lease expired after maximum attempts'),
      updated_at = now()
  WHERE status = 'running'
    AND locked_at < now() - interval '15 minutes'
    AND attempts >= max_attempts;

  RETURN QUERY
  WITH candidates AS (
    SELECT t.id
    FROM public.office_tasks AS t
    WHERE (
      (t.status = 'queued' AND t.run_at <= now())
      OR
      (t.status = 'running' AND t.locked_at < now() - interval '15 minutes')
    )
      AND t.attempts < t.max_attempts
    ORDER BY t.priority DESC, t.run_at ASC, t.created_at ASC
    FOR UPDATE SKIP LOCKED
    LIMIT greatest(1, least(coalesce(p_limit, 1), 10))
  )
  UPDATE public.office_tasks AS t
  SET status = 'running',
      locked_at = now(),
      attempts = t.attempts + 1,
      updated_at = now()
  FROM candidates
  WHERE t.id = candidates.id
  RETURNING t.*;
END;
$function$;

CREATE OR REPLACE FUNCTION public.natasha_claim_jobs(p_limit integer DEFAULT 1)
RETURNS SETOF public.natasha_jobs
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path TO ''
AS $function$
BEGIN
  UPDATE public.natasha_jobs
  SET status = 'failed',
      locked_at = NULL,
      last_error = COALESCE(last_error, 'Worker lease expired after maximum attempts'),
      updated_at = now()
  WHERE status = 'running'
    AND locked_at < now() - interval '15 minutes'
    AND attempts >= max_attempts;

  RETURN QUERY
  WITH candidates AS (
    SELECT j.id
    FROM public.natasha_jobs AS j
    WHERE (
      (j.status = 'queued' AND j.run_at <= now())
      OR
      (j.status = 'running' AND j.locked_at < now() - interval '15 minutes')
    )
      AND j.attempts < j.max_attempts
    ORDER BY j.run_at ASC, j.created_at ASC
    FOR UPDATE SKIP LOCKED
    LIMIT least(greatest(coalesce(p_limit, 1), 1), 10)
  )
  UPDATE public.natasha_jobs AS j
  SET status = 'running',
      locked_at = now(),
      attempts = j.attempts + 1,
      updated_at = now()
  FROM candidates
  WHERE j.id = candidates.id
  RETURNING j.*;
END;
$function$;

REVOKE ALL ON FUNCTION public.office_claim_tasks(integer) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.office_claim_tasks(integer) TO service_role;

REVOKE ALL ON FUNCTION public.natasha_claim_jobs(integer) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.natasha_claim_jobs(integer) TO service_role;

ALTER POLICY natasha_activities_owner_all ON public.natasha_activities TO authenticated;
ALTER POLICY natasha_audit_events_owner_all ON public.natasha_audit_events TO authenticated;
ALTER POLICY natasha_companies_owner_all ON public.natasha_companies TO authenticated;
ALTER POLICY natasha_contacts_owner_all ON public.natasha_contacts TO authenticated;
ALTER POLICY natasha_follow_ups_owner_all ON public.natasha_follow_ups TO authenticated;
ALTER POLICY natasha_jobs_owner_all ON public.natasha_jobs TO authenticated;
ALTER POLICY natasha_leads_owner_all ON public.natasha_leads TO authenticated;
ALTER POLICY natasha_message_drafts_owner_all ON public.natasha_message_drafts TO authenticated;
