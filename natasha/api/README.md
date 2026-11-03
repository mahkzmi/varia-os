# Run Natasha API locally

This API is isolated from the existing Streamlit application.

## 1. Apply the database migration
Review and run `supabase/migrations/202611030001_natasha_sales_engine.sql` in the SQL Editor of the existing Varia OS Supabase project.

## 2. Configure the API
Create a local `.env` file based on `.env.example`. Use the Supabase project URL and the server-side service-role key. Never expose the service-role key in a browser, commit it, or paste it into chat.

## 3. Install and run
From this directory:

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt
uvicorn main:app --reload
```

Open `/health` for the health check and `/docs` for the API schema.

## Authentication
Protected endpoints expect a Supabase Auth access token in the Authorization header:

`Authorization: Bearer <access-token>`

The API validates the token with Supabase Auth. The service-role key is used only on the server.

## Current endpoints
- `GET /health`
- `GET /api/leads`
- `POST /api/leads`
- `PATCH /api/leads/{lead_id}`

The existing Streamlit app is not changed by this API scaffold.
