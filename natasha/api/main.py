from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from supabase import Client, create_client

from .settings import settings

app = FastAPI(title="Natasha API", version="0.1.0", docs_url="/docs")

class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=8)



def get_db() -> Client:
    if not settings.supabase_url or not settings.supabase_publishable_key:
        raise HTTPException(status_code=503, detail="Supabase URL or publishable key is missing")
    return create_client(settings.supabase_url, settings.supabase_publishable_key)


bearer_scheme = HTTPBearer(auto_error=False)


def current_user_id(
    db: Annotated[Client, Depends(get_db)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required")
    token = credentials.credentials
    try:
        user = db.auth.get_user(token)
        if not user or not user.user:
            raise ValueError("No authenticated user")
        # Run all subsequent PostgREST queries with the caller's JWT so RLS
        # evaluates auth.uid() as the authenticated owner, not service_role.
        db.postgrest.auth(token)
        return str(user.user.id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired access token")


def validate_owned_relations(
    db: Client,
    user_id: str,
    company_id: UUID | None,
    primary_contact_id: UUID | None,
) -> None:
    if company_id:
        company = (
            db.table("natasha_companies")
            .select("id")
            .eq("id", str(company_id))
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        if not company.data:
            raise HTTPException(status_code=422, detail="Company not found for this user")

    if primary_contact_id:
        contact = (
            db.table("natasha_contacts")
            .select("id,company_id")
            .eq("id", str(primary_contact_id))
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        if not contact.data:
            raise HTTPException(status_code=422, detail="Contact not found for this user")
        linked_company_id = contact.data[0].get("company_id")
        if company_id and linked_company_id and linked_company_id != str(company_id):
            raise HTTPException(status_code=422, detail="Contact does not belong to the selected company")


class LeadCreate(BaseModel):
    product: str = Field(pattern=r"^(Varia Carbon|Varia Vision|Varia Trait-Bridge|Other)$")
    company_id: UUID | None = None
    primary_contact_id: UUID | None = None
    stage: str = Field(default="new", pattern=r"^(new|researching|qualified|contacted|replied|meeting|proposal|pilot|won|disqualified|lost)$")
    source: str | None = None
    estimated_value: float | None = Field(default=None, ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    next_action: str | None = None
    next_action_at: datetime | None = None
    notes: str | None = None


class LeadUpdate(BaseModel):
    product: str | None = Field(default=None, pattern=r"^(Varia Carbon|Varia Vision|Varia Trait-Bridge|Other)$")
    stage: str | None = Field(default=None, pattern=r"^(new|researching|qualified|contacted|replied|meeting|proposal|pilot|won|disqualified|lost)$")
    source: str | None = None
    fit_score: int | None = Field(default=None, ge=0, le=100)
    fit_rationale: str | None = None
    estimated_value: float | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    next_action: str | None = None
    next_action_at: datetime | None = None
    notes: str | None = None


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "Natasha API", "status": "online", "docs": "/docs", "health": "/health"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "natasha-api"}


@app.post("/api/auth/login")
def login(payload: LoginRequest) -> dict:
    if not settings.supabase_publishable_key:
        raise HTTPException(status_code=503, detail="Supabase publishable key is not configured")
    try:
        auth_client = create_client(settings.supabase_url, settings.supabase_publishable_key)
        session = auth_client.auth.sign_in_with_password({
            "email": payload.email,
            "password": payload.password,
        })
        if not session.session:
            raise ValueError("No session returned")
        return {
            "access_token": session.session.access_token,
            "token_type": "bearer",
            "expires_in": session.session.expires_in,
            "user": {"id": session.user.id, "email": session.user.email},
        }
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid email or password")


@app.get("/api/leads")
def list_leads(
    user_id: Annotated[str, Depends(current_user_id)],
    db: Annotated[Client, Depends(get_db)],
) -> list[dict]:
    response = (
        db.table("natasha_leads")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    return response.data or []


@app.post("/api/leads", status_code=status.HTTP_201_CREATED)
def create_lead(
    payload: LeadCreate,
    user_id: Annotated[str, Depends(current_user_id)],
    db: Annotated[Client, Depends(get_db)],
) -> dict:
    validate_owned_relations(db, user_id, payload.company_id, payload.primary_contact_id)
    row = payload.model_dump(mode="json")
    row["user_id"] = user_id
    response = db.table("natasha_leads").insert(row).execute()
    if not response.data:
        raise HTTPException(status_code=500, detail="Lead could not be created")
    lead = response.data[0]
    db.table("natasha_audit_events").insert({
        "user_id": user_id,
        "entity_type": "lead",
        "entity_id": lead["id"],
        "action": "lead_created",
        "details": {"product": lead["product"], "stage": lead["stage"]},
    }).execute()
    return lead


@app.patch("/api/leads/{lead_id}")
def update_lead(
    lead_id: UUID,
    payload: LeadUpdate,
    user_id: Annotated[str, Depends(current_user_id)],
    db: Annotated[Client, Depends(get_db)],
) -> dict:
    changes = payload.model_dump(exclude_unset=True, mode="json")
    if not changes:
        raise HTTPException(status_code=400, detail="No changes supplied")
    existing = (
        db.table("natasha_leads")
        .select("id,stage")
        .eq("id", str(lead_id))
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Lead not found")
    existing_lead = existing.data[0]
    response = (
        db.table("natasha_leads")
        .update(changes)
        .eq("id", str(lead_id))
        .eq("user_id", user_id)
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=500, detail="Lead could not be updated")
    if "stage" in changes and changes["stage"] != existing_lead["stage"]:
        db.table("natasha_activities").insert({
            "user_id": user_id,
            "lead_id": str(lead_id),
            "activity_type": "stage_change",
            "subject": "Lead stage changed",
            "metadata": {"from": existing_lead["stage"], "to": changes["stage"]},
        }).execute()
    return response.data[0]


class CompanyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    website: str | None = None
    industry: str | None = None
    country: str | None = None
    notes: str | None = None
    source: str | None = None


class ContactCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    company_id: UUID | None = None
    role: str | None = None
    email: str | None = None
    linkedin_url: str | None = None
    is_decision_maker: bool = False
    notes: str | None = None


class FollowUpCreate(BaseModel):
    lead_id: UUID
    title: str = Field(min_length=1, max_length=240)
    due_at: datetime


class DraftCreate(BaseModel):
    lead_id: UUID | None = None
    recipient: str
    subject: str = Field(min_length=1, max_length=300)
    body: str = Field(min_length=1)


def require_owned_record(db: Client, table: str, record_id: UUID, user_id: str) -> dict:
    result = (
        db.table(table).select("*")
        .eq("id", str(record_id)).eq("user_id", user_id)
        .limit(1).execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail=f"{table.rstrip('s')} not found")
    return result.data[0]


@app.get("/api/companies")
def list_companies(
    user_id: Annotated[str, Depends(current_user_id)],
    db: Annotated[Client, Depends(get_db)],
) -> list[dict]:
    result = db.table("natasha_companies").select("*").eq("user_id", user_id).order("name").execute()
    return result.data or []


@app.post("/api/companies", status_code=status.HTTP_201_CREATED)
def create_company(
    payload: CompanyCreate,
    user_id: Annotated[str, Depends(current_user_id)],
    db: Annotated[Client, Depends(get_db)],
) -> dict:
    row = {**payload.model_dump(), "user_id": user_id}
    result = db.table("natasha_companies").insert(row).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Company could not be created")
    company = result.data[0]
    db.table("natasha_audit_events").insert({
        "user_id": user_id, "entity_type": "company", "entity_id": company["id"],
        "action": "company_created", "details": {"name": company["name"]},
    }).execute()
    return company


@app.get("/api/contacts")
def list_contacts(
    user_id: Annotated[str, Depends(current_user_id)],
    db: Annotated[Client, Depends(get_db)],
) -> list[dict]:
    result = db.table("natasha_contacts").select("*").eq("user_id", user_id).order("full_name").execute()
    return result.data or []


@app.post("/api/contacts", status_code=status.HTTP_201_CREATED)
def create_contact(
    payload: ContactCreate,
    user_id: Annotated[str, Depends(current_user_id)],
    db: Annotated[Client, Depends(get_db)],
) -> dict:
    if payload.company_id:
        require_owned_record(db, "natasha_companies", payload.company_id, user_id)
    row = {**payload.model_dump(mode="json"), "user_id": user_id}
    result = db.table("natasha_contacts").insert(row).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Contact could not be created")
    contact = result.data[0]
    db.table("natasha_audit_events").insert({
        "user_id": user_id, "entity_type": "contact", "entity_id": contact["id"],
        "action": "contact_created", "details": {"full_name": contact["full_name"]},
    }).execute()
    return contact


@app.get("/api/follow-ups")
def list_follow_ups(
    user_id: Annotated[str, Depends(current_user_id)],
    db: Annotated[Client, Depends(get_db)],
) -> list[dict]:
    result = db.table("natasha_follow_ups").select("*").eq("user_id", user_id).order("due_at").execute()
    return result.data or []


@app.post("/api/follow-ups", status_code=status.HTTP_201_CREATED)
def create_follow_up(
    payload: FollowUpCreate,
    user_id: Annotated[str, Depends(current_user_id)],
    db: Annotated[Client, Depends(get_db)],
) -> dict:
    require_owned_record(db, "natasha_leads", payload.lead_id, user_id)
    row = {**payload.model_dump(mode="json"), "user_id": user_id}
    result = db.table("natasha_follow_ups").insert(row).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Follow-up could not be created")
    item = result.data[0]
    db.table("natasha_audit_events").insert({
        "user_id": user_id, "entity_type": "follow_up", "entity_id": item["id"],
        "action": "follow_up_created", "details": {"lead_id": str(payload.lead_id)},
    }).execute()
    return item


@app.get("/api/drafts")
def list_drafts(
    user_id: Annotated[str, Depends(current_user_id)],
    db: Annotated[Client, Depends(get_db)],
) -> list[dict]:
    result = db.table("natasha_message_drafts").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
    return result.data or []


@app.post("/api/drafts", status_code=status.HTTP_201_CREATED)
def create_draft(
    payload: DraftCreate,
    user_id: Annotated[str, Depends(current_user_id)],
    db: Annotated[Client, Depends(get_db)],
) -> dict:
    if payload.lead_id:
        require_owned_record(db, "natasha_leads", payload.lead_id, user_id)
    row = {**payload.model_dump(mode="json"), "user_id": user_id}
    result = db.table("natasha_message_drafts").insert(row).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Draft could not be created")
    draft = result.data[0]
    db.table("natasha_audit_events").insert({
        "user_id": user_id, "entity_type": "message_draft", "entity_id": draft["id"],
        "action": "draft_created", "details": {"recipient": draft["recipient"]},
    }).execute()
    return draft


@app.post("/api/drafts/{draft_id}/approve")
def approve_draft(
    draft_id: UUID,
    user_id: Annotated[str, Depends(current_user_id)],
    db: Annotated[Client, Depends(get_db)],
) -> dict:
    draft = require_owned_record(db, "natasha_message_drafts", draft_id, user_id)
    if draft["status"] != "draft":
        raise HTTPException(status_code=409, detail="Only drafts can be approved")
    result = (
        db.table("natasha_message_drafts")
        .update({"status": "approved", "approved_at": datetime.now().astimezone().isoformat()})
        .eq("id", str(draft_id)).eq("user_id", user_id).execute()
    )
    if not result.data:
        raise HTTPException(status_code=500, detail="Draft approval failed")
    db.table("natasha_audit_events").insert({
        "user_id": user_id, "entity_type": "message_draft", "entity_id": str(draft_id),
        "action": "draft_approved", "details": {"send_enabled": False},
    }).execute()
    return result.data[0]


# --- Natasha AI Sales Engine -------------------------------------------------

class AgentRunRequest(BaseModel):
    product: str = Field(pattern=r"^(Varia Carbon|Varia Vision|Varia Trait-Bridge)$")
    target_market: str = Field(min_length=2, max_length=160)
    ideal_customer: str = Field(min_length=10, max_length=1200)
    max_companies: int = Field(default=5, ge=1, le=10)


def _sales_system_prompt() -> str:
    return """You are Natasha, the research-led sales intelligence agent for Varia Studio,
an independent AgTech AI studio. Products:
- Varia Carbon: soil organic carbon estimation/intelligence from environmental and satellite data.
- Varia Vision: computer-vision crop/weed detection and field image analysis.
- Varia Trait-Bridge: an early-stage plant-trait / phenotyping product; do not claim capabilities not supplied.
Your job: qualify companies as potential buyers/partners. Use ONLY supplied search results as factual evidence.
Never invent company facts, people, emails, revenue, customers, or product capabilities.
Return strict JSON with key 'leads', an array. Each item: company_name, website, country,
industry, fit_score (0-100 integer), fit_rationale, evidence (array of short strings),
recommended_angle, next_action, contact_role, email_subject, email_body.
If evidence is weak, lower score and explicitly say what is unknown. Draft concise, specific,
professional outreach. The human sender is Mahdieh Kazemi, Founder of Varia Studio. Never introduce the AI agent as the sender and never sign as Natasha. Write in Mahdieh's first-person founder voice and use this sign-off: Best regards, Mahdieh Kazemi, Founder of Varia Studio. Do not imply a relationship or claim that Varia has results it has not proven.
Return no markdown fences."""


@app.post("/api/agent/run")
async def run_sales_agent(
    payload: AgentRunRequest,
    user_id: Annotated[str, Depends(current_user_id)],
    db: Annotated[Client, Depends(get_db)],
) -> dict:
    if not settings.tavily_api_key:
        raise HTTPException(status_code=503, detail="TAVILY_API_KEY is not configured")
    if not settings.llm_api_key:
        raise HTTPException(status_code=503, detail="LLM_API_KEY is not configured")

    import json
    import httpx

    query = (
        f"companies organizations {payload.target_market} {payload.ideal_customer} "
        f"related to {payload.product} agriculture technology"
    )
    async with httpx.AsyncClient(timeout=45.0) as client:
        search_response = await client.post(
            "https://api.tavily.com/search",
            json={
                "api_key": settings.tavily_api_key,
                "query": query,
                "search_depth": "advanced",
                "max_results": min(payload.max_companies * 3, 20),
                "include_answer": False,
            },
        )
        if search_response.status_code >= 400:
            raise HTTPException(status_code=502, detail="Web research provider returned an error")
        search_data = search_response.json()
        search_results = search_data.get("results", [])
        if not search_results:
            return {"status": "no_results", "leads_created": 0, "leads": []}

        llm_url = f"{settings.llm_base_url.rstrip('/')}/chat/completions"
        llm_headers = {"Authorization": f"Bearer {settings.llm_api_key}"}
        llm_payload = {
            "model": settings.llm_model,
            "temperature": 0.1,
            "messages": [
                {"role": "system", "content": _sales_system_prompt()},
                {"role": "user", "content": json.dumps({
                    "product": payload.product,
                    "target_market": payload.target_market,
                    "ideal_customer": payload.ideal_customer,
                    "search_results": [
                        {"title": x.get("title"), "url": x.get("url"), "content": str(x.get("content", ""))[:2500]}
                        for x in search_results
                    ],
                    "max_companies": payload.max_companies,
                }, ensure_ascii=False)},
            ],
        }
        llm_response = await client.post(
            llm_url, headers=llm_headers,
            json={**llm_payload, "response_format": {"type": "json_object"}},
        )
        # Some OpenAI-compatible free models do not support response_format.
        if llm_response.status_code in (400, 422):
            llm_response = await client.post(llm_url, headers=llm_headers, json=llm_payload)
        if llm_response.status_code >= 400:
            raise HTTPException(status_code=502, detail=f"LLM provider request failed (HTTP {llm_response.status_code})")
        def parse_llm_json(response):
            data = response.json()
            choices = data.get("choices") or []
            if not choices:
                raise ValueError("provider returned no choices")
            message = choices[0].get("message") or {}
            content = message.get("content")
            if isinstance(content, list):
                content = "".join(
                    part.get("text", "") for part in content if isinstance(part, dict)
                )
            if not isinstance(content, str) or not content.strip():
                raise ValueError("provider returned empty message content")
            cleaned = content.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\\n", 1)[-1]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3].strip()
            try:
                parsed = json.loads(cleaned)
            except ValueError:
                start, end = cleaned.find("{"), cleaned.rfind("}")
                if start < 0 or end <= start:
                    raise
                parsed = json.loads(cleaned[start:end + 1])
            if not isinstance(parsed, dict) or not isinstance(parsed.get("leads"), list):
                raise ValueError("JSON must contain a leads array")
            return parsed, message, choices[0].get("finish_reason")

        try:
            result, llm_message, finish_reason = parse_llm_json(llm_response)
            # A syntactically valid but empty array is not a successful sales-research run.
            if not result.get("leads"):
                retry_payload = {
                    **llm_payload,
                    "messages": llm_payload["messages"] + [
                        {"role": "assistant", "content": json.dumps(result, ensure_ascii=False)},
                        {"role": "user", "content": (
                            "Your previous JSON was valid but returned an empty leads array. "
                            "Re-examine ONLY the supplied search results. If any identifiable organization "
                            "is relevant or plausibly adjacent to the target customer profile, include the "
                            "best candidate(s), up to max_companies. Use a conservative fit_score and clearly "
                            "state uncertainty. Do not invent facts, people, emails, or capabilities. "
                            'Return only JSON with a non-empty "leads" array when evidence supports a candidate; '
                            'otherwise return {"leads": []}.'
                        )},
                    ],
                }
                retry_response = await client.post(
                    llm_url, headers=llm_headers,
                    json={**retry_payload, "response_format": {"type": "json_object"}},
                )
                if retry_response.status_code in (400, 422):
                    retry_response = await client.post(llm_url, headers=llm_headers, json=retry_payload)
                if retry_response.status_code >= 400:
                    raise HTTPException(status_code=502, detail="LLM returned no leads and the research retry failed")
                result, llm_message, finish_reason = parse_llm_json(retry_response)
                if not result.get("leads"):
                    raise HTTPException(
                        status_code=502,
                        detail=f"No defensible companies found in {len(search_results)} web search results; no leads were saved",
                    )
        except (KeyError, IndexError, TypeError, ValueError):
            # Ask the same model to repair its own output once; never persist malformed data.
            try:
                raw_content = llm_response.json()["choices"][0]["message"].get("content", "")
                repair_payload = {
                    **llm_payload,
                    "messages": llm_payload["messages"] + [
                        {"role": "assistant", "content": str(raw_content)[:12000]},
                        {"role": "user", "content": (
                            "Your previous response was not valid JSON. Return ONLY one valid JSON object "
                            'with a top-level "leads" array. Do not use markdown fences or commentary. '
                            "Preserve the facts and do not add unsupported claims."
                        )},
                    ],
                }
                repair_response = await client.post(
                    llm_url, headers=llm_headers,
                    json={**repair_payload, "response_format": {"type": "json_object"}},
                )
                if repair_response.status_code in (400, 422):
                    repair_response = await client.post(
                        llm_url, headers=llm_headers, json=repair_payload
                    )
                if repair_response.status_code >= 400:
                    raise ValueError("provider rejected JSON repair request")
                result, llm_message, finish_reason = parse_llm_json(repair_response)
            except (KeyError, IndexError, TypeError, ValueError):
                raise HTTPException(
                    status_code=502,
                    detail="LLM could not produce valid JSON after one repair attempt; no leads were saved",
                )

    created = []
    for item in result.get("leads", [])[:payload.max_companies]:
        name = str(item.get("company_name", "")).strip()
        if not name:
            continue
        website = item.get("website")
        existing = (
            db.table("natasha_companies").select("id")
            .eq("user_id", user_id).eq("name", name).limit(1).execute()
        )
        if existing.data:
            company_id = existing.data[0]["id"]
        else:
            company_row = {
                "user_id": user_id, "name": name, "website": website,
                "industry": item.get("industry"), "country": item.get("country"),
                "source": "natasha_ai_research",
                "notes": json.dumps({"evidence": item.get("evidence", [])}, ensure_ascii=False),
            }
            company_result = db.table("natasha_companies").insert(company_row).execute()
            if not company_result.data:
                continue
            company_id = company_result.data[0]["id"]

        lead_result = db.table("natasha_leads").insert({
            "user_id": user_id, "company_id": company_id, "product": payload.product,
            "stage": "qualified" if int(item.get("fit_score", 0)) >= 70 else "researching",
            "currency": "USD",
            "source": "natasha_ai_research",
            "fit_score": max(0, min(100, int(item.get("fit_score", 0)))),
            "fit_rationale": str(item.get("fit_rationale", ""))[:4000],
            "next_action": str(item.get("next_action", "Review research and identify a decision-maker"))[:1000],
            "notes": json.dumps({
                "evidence": item.get("evidence", []),
                "recommended_angle": item.get("recommended_angle"),
                "contact_role": item.get("contact_role"),
                "contact_email_verified": bool(item.get("contact_email_verified", False)),
            }, ensure_ascii=False),
        }).execute()
        if not lead_result.data:
            continue
        lead = lead_result.data[0]
        draft = db.table("natasha_message_drafts").insert({
            "user_id": user_id, "lead_id": lead["id"], "channel": "email",
            "recipient": (str(item.get("contact_email")).strip() if item.get("contact_email_verified") and item.get("contact_email") else "Decision-maker email not verified — research required"),
            "subject": str(item.get("email_subject", "Exploring a potential AgTech collaboration"))[:300],
            "body": str(item.get("email_body", ""))[:12000],
            "status": "draft",
        }).execute()
        created.append({
            "company": name, "lead": lead,
            "draft": draft.data[0] if draft.data else None,
            "evidence": item.get("evidence", []),
            "recommended_angle": item.get("recommended_angle"),
        })

    db.table("natasha_audit_events").insert({
        "user_id": user_id, "entity_type": "agent_run", "action": "sales_research_completed",
        "details": {"product": payload.product, "target_market": payload.target_market,
                    "leads_created": len(created)},
    }).execute()
    return {"status": "completed", "leads_created": len(created), "leads": created}


# --- Durable background jobs -------------------------------------------------

class AgentJobRequest(AgentRunRequest):
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=160)


@app.post("/api/jobs/agent-run", status_code=status.HTTP_202_ACCEPTED)
def enqueue_agent_run(
    payload: AgentJobRequest,
    user_id: Annotated[str, Depends(current_user_id)],
    db: Annotated[Client, Depends(get_db)],
) -> dict:
    key = payload.idempotency_key or str(uuid4())
    job_payload = payload.model_dump(exclude={"idempotency_key"})
    try:
        result = db.table("natasha_jobs").insert({
            "user_id": user_id,
            "job_type": "agent_run",
            "payload": job_payload,
            "idempotency_key": key,
            "status": "queued",
        }).execute()
    except Exception:
        # An idempotency collision returns the existing job, never creates a duplicate.
        existing = (
            db.table("natasha_jobs").select("*")
            .eq("user_id", user_id).eq("idempotency_key", key).limit(1).execute()
        )
        if existing.data:
            return {"status": "already_queued", "job": existing.data[0]}
        raise HTTPException(status_code=500, detail="Could not enqueue Natasha job")
    if not result.data:
        raise HTTPException(status_code=500, detail="Could not enqueue Natasha job")
    return {"status": "queued", "job": result.data[0]}


@app.get("/api/jobs")
def list_jobs(
    user_id: Annotated[str, Depends(current_user_id)],
    db: Annotated[Client, Depends(get_db)],
) -> list[dict]:
    result = (
        db.table("natasha_jobs").select("*").eq("user_id", user_id)
        .order("created_at", desc=True).limit(50).execute()
    )
    return result.data or []


@app.get("/api/jobs/{job_id}")
def get_job(
    job_id: UUID,
    user_id: Annotated[str, Depends(current_user_id)],
    db: Annotated[Client, Depends(get_db)],
) -> dict:
    result = (
        db.table("natasha_jobs").select("*").eq("id", str(job_id))
        .eq("user_id", user_id).limit(1).execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Job not found")
    return result.data[0]


class InternalAgentRunRequest(BaseModel):
    user_id: UUID
    payload: AgentRunRequest


@app.post("/internal/agent/run")
async def internal_agent_run(
    request: InternalAgentRunRequest,
    x_internal_key: Annotated[str | None, Header(alias="X-Internal-Key")] = None,
) -> dict:
    import hmac
    expected = settings.supabase_service_role_key
    if not expected or not x_internal_key or not hmac.compare_digest(x_internal_key, expected):
        raise HTTPException(status_code=401, detail="Internal worker authentication failed")
    if not settings.supabase_url:
        raise HTTPException(status_code=503, detail="Supabase URL is not configured")
    service_db = create_client(settings.supabase_url, expected)
    return await run_sales_agent(request.payload, str(request.user_id), service_db)
