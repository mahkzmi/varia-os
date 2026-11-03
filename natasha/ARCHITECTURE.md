# Natasha — Architecture and delivery plan

## Product boundary
Natasha owns sales execution: prospects, qualification, pipeline movement, follow-up planning, message drafting, and reporting. Tony owns market discovery and prospect sourcing. Natasha consumes Tony-approved prospects; it does not silently invent verified facts.

## Data flow
Founder / Varia OS UI -> FastAPI -> Supabase Postgres (source of truth)
                                  |
                                  +-> Python worker -> due reminders, draft jobs, approved delivery (later)

## Workflow
1. A prospect is added manually or imported from Tony after review.
2. Natasha records evidence, product fit, and qualification status.
3. Natasha proposes a next action and due date.
4. The founder approves the action; a draft is generated.
5. The founder reviews and approves the exact recipient, subject, and body.
6. Only then may an email provider adapter send it.
7. Delivery outcome and provider message ID are written to the activity log.

## Lead stages
new -> researching -> qualified -> contacted -> replied -> meeting -> proposal -> pilot -> won
Terminal alternatives: disqualified, lost.
Stage changes are explicit and auditable; no silent automatic promotion.

## Initial automation choice (no n8n)
Use a database-backed job queue in Postgres and a lightweight Python worker. This avoids adding a separate automation SaaS or Redis dependency in the first release. Jobs use FOR UPDATE SKIP LOCKED, leases, idempotency keys, bounded attempts, and retry backoff. If throughput later requires it, the worker can move to Celery/Redis or a managed workflow service without changing the domain model.

## Security
- Supabase Auth JWT is the identity boundary.
- Row Level Security is enabled on all user-owned tables.
- The service-role key is server-side only and must never reach the browser.
- Every mutation records actor, action, entity, and timestamp.
- Email send endpoint requires an approved draft and a one-time approval state transition.
- No arbitrary URL fetching from user-provided content in the first release.

## Milestones
### M0 — Foundation
Define schema, security policies, workflow states, and API/worker boundaries. Preserve the existing Streamlit app.

### M1 — Working CRM API
FastAPI app, health endpoint, lead CRUD, stage transitions, activity timeline, and tests for validation and ownership boundaries.

### M2 — Follow-up engine
Postgres job queue, worker, retry policy, and due follow-up view. Dry-run mode by default.

### M3 — AI sales copilot
Evidence-based company briefs, explainable lead scoring, and personalized draft generation. Store sources and uncertainty; never fabricate contact details or claims.

### M4 — Approval-gated email
Connect the selected email provider. Send only the exact approved draft; log provider response. Add unsubscribe and suppression handling before outbound campaign functionality.

## MVP acceptance criteria
- A lead can be created, updated, qualified, and moved through stages.
- Every lead has a visible next action and follow-up date.
- Due follow-ups appear in a queue and can be snoozed or completed.
- A message draft can be created and approved, but cannot be sent without explicit approval.
- All records are user-scoped by RLS.
- No secrets are committed.
