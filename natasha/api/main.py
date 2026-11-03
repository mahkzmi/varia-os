from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from supabase import Client, create_client

from .settings import settings

app = FastAPI(title="Natasha API", version="0.1.0", docs_url="/docs")

class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=8)



def get_db() -> Client:
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise HTTPException(status_code=503, detail="Supabase server configuration is missing")
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


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
            .maybe_single()
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
            .maybe_single()
            .execute()
        )
        if not contact.data:
            raise HTTPException(status_code=422, detail="Contact not found for this user")
        linked_company_id = contact.data.get("company_id")
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
        .maybe_single()
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Lead not found")
    response = (
        db.table("natasha_leads")
        .update(changes)
        .eq("id", str(lead_id))
        .eq("user_id", user_id)
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=500, detail="Lead could not be updated")
    if "stage" in changes and changes["stage"] != existing.data["stage"]:
        db.table("natasha_activities").insert({
            "user_id": user_id,
            "lead_id": str(lead_id),
            "activity_type": "stage_change",
            "subject": "Lead stage changed",
            "metadata": {"from": existing.data["stage"], "to": changes["stage"]},
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
        .maybe_single().execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail=f"{table.rstrip('s')} not found")
    return result.data


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
