# Natasha API

Deployed API for the Natasha MVP. This service is isolated from the existing Streamlit application.

## Live URLs
- API root: https://natasha-api.onrender.com/
- Health: https://natasha-api.onrender.com/health
- Interactive API docs: https://natasha-api.onrender.com/docs

## Required environment variables
Set these in Render (never commit secrets):
- SUPABASE_URL: the Varia OS project URL
- SUPABASE_PUBLISHABLE_KEY: the project's publishable key; used only for password sign-in
- SUPABASE_SERVICE_ROLE_KEY: server-side Supabase secret/service-role key; used only by the API server

Never expose the server-side secret in a browser or paste it into chat.

## Authentication
1. Create a test user in Supabase Dashboard → Authentication → Users.
2. Call POST /api/auth/login with JSON containing email and password.
3. Copy the returned access_token.
4. In Swagger /docs, click Authorize and enter Bearer <access_token>.

Protected endpoints validate the access token with Supabase Auth. The API explicitly scopes database queries by user_id because it uses a privileged server-side key.

## Current endpoints
- GET /health, GET /
- POST /api/auth/login
- GET /api/companies, POST /api/companies
- GET /api/contacts, POST /api/contacts
- GET /api/leads, POST /api/leads, PATCH /api/leads/{lead_id}
- GET /api/follow-ups, POST /api/follow-ups
- GET /api/drafts, POST /api/drafts, POST /api/drafts/{draft_id}/approve

Approving a draft does not send it. External sending is not implemented in this MVP.

## Local run
From this directory:

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn natasha.api.main:app --reload
```
