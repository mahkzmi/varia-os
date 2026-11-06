from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from supabase import Client, create_client

from .settings import settings

router = APIRouter(prefix="/api/office", tags=["Varia AI Office"])
bearer_scheme = HTTPBearer(auto_error=False)


def get_db() -> Client:
    if not settings.supabase_url or not settings.supabase_publishable_key:
        raise HTTPException(status_code=503, detail="Supabase is not configured")
    return create_client(settings.supabase_url, settings.supabase_publishable_key)


def current_user_id(
    db: Annotated[Client, Depends(get_db)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Bearer token required")
    try:
        user = db.auth.get_user(credentials.credentials)
        if not user or not user.user:
            raise ValueError("No authenticated user")
        db.postgrest.auth(credentials.credentials)
        return str(user.user.id)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired access token")


class TaskCreate(BaseModel):
    agent: Literal["natasha", "marketing", "operations"]
    task_type: str = Field(min_length=2, max_length=80)
    title: str = Field(min_length=2, max_length=240)
    description: str | None = Field(default=None, max_length=6000)
    payload: dict = Field(default_factory=dict)
    priority: int = Field(default=3, ge=1, le=5)
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=160)


class ApprovalReview(BaseModel):
    decision: Literal["approved", "rejected"]
    note: str | None = Field(default=None, max_length=2000)


class ContentDraftCreate(BaseModel):
    platform: Literal["instagram", "linkedin", "website", "other"]
    account_type: Literal["personal", "company"] | None = None
    title: str = Field(min_length=2, max_length=240)
    body: str = Field(min_length=1, max_length=20000)
    media_brief: str | None = Field(default=None, max_length=4000)
    scheduled_for: datetime | None = None
    metadata: dict = Field(default_factory=dict)


@router.get("/agents")
def list_agents() -> list[dict]:
    return [
        {"id": "natasha", "name": "Natasha", "role": "Growth & Sales", "status": "active",
         "scope": ["market_research", "lead_scoring", "crm", "outreach_drafts"]},
        {"id": "marketing", "name": "Marketing Agent", "role": "Brand & Content", "status": "configured",
         "scope": ["instagram_planning", "linkedin_strategy", "content_drafts", "website_checks"]},
        {"id": "operations", "name": "Operations Agent", "role": "Studio Operations", "status": "configured",
         "scope": ["proposals", "documents", "project_tracking", "operational_reports"]},
    ]


@router.get("/overview")
def office_overview(
    user_id: Annotated[str, Depends(current_user_id)],
    db: Annotated[Client, Depends(get_db)],
) -> dict:
    def count(table: str, column: str = "id", value: str | None = None) -> int:
        query = db.table(table).select(column, count="exact").eq("user_id", user_id)
        if value is not None:
            query = query.eq("status", value)
        result = query.limit(1).execute()
        return int(result.count or 0)

    return {
        "tasks": count("office_tasks"),
        "queued_tasks": count("office_tasks", value="queued"),
        "running_tasks": count("office_tasks", value="running"),
        "pending_approvals": count("office_approvals", value="pending"),
        "content_drafts": count("office_content_drafts", value="draft"),
        "agents": 3,
        "autonomy_level": "limited",
        "email_provider": "gmail",
    }


@router.get("/tasks")
def list_tasks(
    user_id: Annotated[str, Depends(current_user_id)],
    db: Annotated[Client, Depends(get_db)],
) -> list[dict]:
    result = (db.table("office_tasks").select("*").eq("user_id", user_id)
              .order("created_at", desc=True).limit(100).execute())
    return result.data or []


@router.post("/tasks", status_code=status.HTTP_202_ACCEPTED)
def create_task(
    payload: TaskCreate,
    user_id: Annotated[str, Depends(current_user_id)],
    db: Annotated[Client, Depends(get_db)],
) -> dict:
    row = payload.model_dump(exclude={"idempotency_key"})
    row.update({"user_id": user_id, "status": "queued"})
    try:
        result = db.table("office_tasks").insert({
            **row, "idempotency_key": payload.idempotency_key
        }).execute()
    except Exception:
        if payload.idempotency_key:
            existing = (db.table("office_tasks").select("*").eq("user_id", user_id)
                        .eq("idempotency_key", payload.idempotency_key).limit(1).execute())
            if existing.data:
                return {"status": "already_queued", "task": existing.data[0]}
        raise HTTPException(status_code=500, detail="Could not queue office task")
    if not result.data:
        raise HTTPException(status_code=500, detail="Could not queue office task")
    return {"status": "queued", "task": result.data[0]}


@router.get("/approvals")
def list_approvals(
    user_id: Annotated[str, Depends(current_user_id)],
    db: Annotated[Client, Depends(get_db)],
) -> list[dict]:
    result = (db.table("office_approvals").select("*").eq("user_id", user_id)
              .order("created_at", desc=True).limit(100).execute())
    return result.data or []


@router.post("/approvals/{approval_id}/review")
def review_approval(
    approval_id: UUID,
    payload: ApprovalReview,
    user_id: Annotated[str, Depends(current_user_id)],
    db: Annotated[Client, Depends(get_db)],
) -> dict:
    existing = (db.table("office_approvals").select("id,status").eq("id", str(approval_id))
                .eq("user_id", user_id).limit(1).execute())
    if not existing.data:
        raise HTTPException(status_code=404, detail="Approval not found")
    if existing.data[0]["status"] != "pending":
        raise HTTPException(status_code=409, detail="This approval has already been reviewed")
    result = (db.table("office_approvals").update({
        "status": payload.decision,
        "review_note": payload.note,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", str(approval_id)).eq("user_id", user_id).execute())
    return result.data[0] if result.data else {"status": payload.decision}


@router.get("/settings")
def get_office_settings(
    user_id: Annotated[str, Depends(current_user_id)],
    db: Annotated[Client, Depends(get_db)],
) -> dict:
    result = db.table("office_settings").select("*").eq("user_id", user_id).limit(1).execute()
    if result.data:
        return result.data[0]
    created = db.table("office_settings").insert({
        "user_id": user_id, "email_provider": "gmail", "autonomy_level": "limited"
    }).execute()
    return created.data[0] if created.data else {
        "user_id": user_id, "email_provider": "gmail", "autonomy_level": "limited"
    }


@router.get("/content")
def list_content(
    user_id: Annotated[str, Depends(current_user_id)],
    db: Annotated[Client, Depends(get_db)],
) -> list[dict]:
    result = (db.table("office_content_drafts").select("*").eq("user_id", user_id)
              .order("created_at", desc=True).limit(100).execute())
    return result.data or []


@router.post("/content", status_code=status.HTTP_201_CREATED)
def create_content(
    payload: ContentDraftCreate,
    user_id: Annotated[str, Depends(current_user_id)],
    db: Annotated[Client, Depends(get_db)],
) -> dict:
    row = payload.model_dump(mode="json")
    row.update({"user_id": user_id, "agent": "marketing", "status": "draft"})
    result = db.table("office_content_drafts").insert(row).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Could not save content draft")
    return result.data[0]
