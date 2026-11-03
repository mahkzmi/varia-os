from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field
from supabase import Client, create_client

from .settings import settings

app = FastAPI(title="Natasha API", version="0.1.0", docs_url="/docs")


def get_db() -> Client:
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise HTTPException(status_code=503, detail="Supabase server configuration is missing")
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def current_user_id(
    authorization: Annotated[str | None, Header()] = None,
    db: Annotated[Client, Depends(get_db)] = None,
) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required")
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required")
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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "natasha-api"}


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
