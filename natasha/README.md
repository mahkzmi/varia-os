# Natasha — Varia OS Sales & Growth Engine

Natasha is the sales operations module of Varia OS. It is designed for a founder-led B2B studio and starts with human-approved workflows.

## First release (MVP)
1. Company and contact records.
2. Lead pipeline with product interest, source, owner, value estimate, stage, and next action.
3. Activity timeline.
4. Follow-up queue with due dates and retry-safe job records.
5. AI-assisted account briefs and message drafts (draft only).
6. Approval gate before any external email is sent.
7. Audit log for every state-changing action.

## Explicit non-goals for v1
- No autonomous email sending.
- No automatic price or contract commitments.
- No scraping behind logins or bypassing access controls.
- No dependence on n8n.

## Initial stack
- FastAPI application API.
- Supabase Postgres as the source of truth.
- Small Python worker using Postgres row locking for scheduled jobs.
- Provider adapters for email and LLM services.
- Existing Streamlit app remains untouched while Natasha is built alongside it.

## Safety model
- Every business record is scoped to its creator (user_id).
- External messages are drafts and require explicit approval.
- Worker jobs are idempotent and have bounded retries.
- Secrets stay in deployment environment variables; never commit them.

## Build sequence
See ARCHITECTURE.md. The first database migration is in ../supabase/migrations/202611030001_natasha_sales_engine.sql.
