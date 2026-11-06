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
        {"id": "marketing", "name": "Tony", "role": "Brand & Content · Creative Lead", "status": "configured",
         "scope": ["instagram_planning", "linkedin_strategy", "content_drafts", "website_checks"]},
        {"id": "operations", "name": "Edith", "role": "Studio Operations · Chief of Staff", "status": "configured",
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


# --- Internal execution endpoint (worker-only) -------------------------------
class OfficeTaskRunRequest(BaseModel):
    user_id: UUID
    task: dict


@router.post("/internal/run")
async def run_office_task(
    request: OfficeTaskRunRequest,
    x_internal_key: Annotated[str | None, __import__("fastapi").Header(alias="X-Internal-Key")] = None,
) -> dict:
    import hmac
    import json
    import time
    import httpx

    expected = settings.supabase_service_role_key
    if not expected or not x_internal_key or not hmac.compare_digest(x_internal_key, expected):
        raise HTTPException(status_code=401, detail="Internal worker authentication failed")
    if not settings.supabase_url:
        raise HTTPException(status_code=503, detail="Supabase is not configured")

    task = request.task
    user_id = str(request.user_id)
    agent = task.get("agent")
    if agent not in {"natasha", "marketing", "operations"}:
        raise HTTPException(status_code=422, detail="Unsupported agent")
    db = create_client(settings.supabase_url, expected)
    started = time.monotonic()
    run_result = db.table("office_agent_runs").insert({
        "user_id": user_id, "task_id": task.get("id"), "agent": agent,
        "model": settings.llm_model, "input_summary": str(task.get("title", ""))[:1000],
        "status": "running",
    }).execute()
    run_id = run_result.data[0]["id"] if run_result.data else None

    try:
        if agent == "natasha":
            from .main import AgentRunRequest, run_sales_agent
            payload = task.get("payload") or {}
            ideal = str(payload.get("ideal_customer") or task.get("description") or
                "Agricultural drone and aerial-imagery providers, crop scouting and agronomy services, and AgTech crop-monitoring platforms with an evidenced field-imagery workflow.")
            sales_request = AgentRunRequest(
                product=payload.get("product", "Varia Vision"),
                target_market=payload.get("target_market", "Global"),
                ideal_customer=ideal[:1200],
                max_companies=int(payload.get("max_companies", 3)),
            )
            output = await run_sales_agent(sales_request, user_id, db)
        else:
            if not settings.llm_api_key:
                raise HTTPException(status_code=503, detail="LLM_API_KEY is not configured")
            if agent == "marketing":
                system_prompt = """You are Tony, Varia Studio's playful, cheeky, charming creative and marketing agent. Your personality is a playful boy with lightly flirty, witty energy in internal conversation; never make external brand content sexually suggestive, unprofessional, pushy, or inappropriate. You are a sharp creative strategist and excellent copywriter. Work only from the supplied task and brand context. Follow the existing personal Instagram strategy for @mahdieh.codes: the founder is the protagonist; the page is not merely a product feed. Brand line: 'Building things & figuring things out.' Voice: Persian-first where appropriate, bilingual selectively, warm, human, conversational, dry understated humour; no corporate/AI clichés, no exaggerated claims, no excessive emojis. Existing Instagram cadence: Monday 20:30 Building Varia (English), Wednesday 20:30 Soil Notes (Persian), Friday 20:30 Founder Diaries / Open Tabs / Off the Clock (Persian), Iran time. Also prepare separate LinkedIn strategy for Varia Studio company page and founder profile when asked. Never publish or send anything. Return strict JSON: summary, deliverable, platform, account_type, title, body, media_brief, approval_request (null unless a specific external action needs founder approval)."""
            else:
                system_prompt = """You are Edith, Varia Studio's mischievous, funny, sharp daughter-like Chief of Staff. You are witty and lively in internal conversation, but exceptionally rigorous, reliable, organised and professional in execution. Prepare proposals, project briefs, reports, delivery plans and Gamma-ready presentation outlines using only the supplied context. Never invent prices, customer names, metrics, team capacity, legal terms, technical capabilities or commitments. Mark missing information explicitly as [NEEDS FOUNDER INPUT]. Use the supplied source document as the only authority when the task identifies one. Never send, sign, publish, negotiate, quote final prices or make commitments. Return strict JSON: summary, deliverable, sections (array), open_questions (array), approval_request (null unless an external commitment is proposed)."""
            user_payload = {
                "agent": agent, "task_type": task.get("task_type"),
                "title": task.get("title"), "description": task.get("description"),
                "payload": task.get("payload") or {},
                "autonomy": "limited; internal preparation only; external actions require founder approval",
            }
            llm_payload = {
                "model": settings.llm_model, "temperature": 0.2,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
                ],
            }
            async with httpx.AsyncClient(timeout=90.0) as client:
                response = await client.post(
                    f"{settings.llm_base_url.rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                    json=llm_payload,
                )
                if response.status_code in (400, 422):
                    llm_payload.pop("response_format", None)
                    response = await client.post(
                        f"{settings.llm_base_url.rstrip('/')}/chat/completions",
                        headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                        json=llm_payload,
                    )
                response.raise_for_status()
            raw = response.json()["choices"][0]["message"]["content"]
            if isinstance(raw, list):
                raw = "".join(part.get("text", "") for part in raw if isinstance(part, dict))
            fence = chr(96) * 3
            cleaned = str(raw).strip().replace(fence + "json", "").replace(fence, "").strip()
            output = json.loads(cleaned)

            if agent == "marketing" and output.get("body"):
                task_payload = task.get("payload") or {}
                platform = output.get("platform") if output.get("platform") in {"instagram", "linkedin", "website", "other"} else task_payload.get("platform", "instagram")
                account_type = output.get("account_type") if output.get("account_type") in {"personal", "company"} else task_payload.get("account_type", "personal")
                db.table("office_content_drafts").insert({
                    "user_id": user_id, "agent": "marketing", "platform": platform,
                    "account_type": account_type, "title": str(output.get("title") or task.get("title"))[:240],
                    "body": str(output.get("body"))[:20000],
                    "media_brief": str(output.get("media_brief") or "")[:4000],
                    "status": "draft", "metadata": {"task_id": task.get("id"), "summary": output.get("summary")},
                }).execute()

            approval = output.get("approval_request")
            if isinstance(approval, dict):
                allowed = {"send_email", "publish_content", "external_message", "pricing", "negotiation", "contract", "financial_commitment", "website_change", "other"}
                action_type = approval.get("action_type")
                if action_type in allowed:
                    db.table("office_approvals").insert({
                        "user_id": user_id, "task_id": task.get("id"), "agent": agent,
                        "action_type": action_type,
                        "title": str(approval.get("title") or "Founder approval required")[:240],
                        "summary": str(approval.get("summary") or "")[:4000],
                        "proposed_payload": approval.get("payload") if isinstance(approval.get("payload"), dict) else {},
                        "status": "pending",
                    }).execute()

        duration = int((time.monotonic() - started) * 1000)
        db.table("office_tasks").update({
            "status": "succeeded", "result": output, "completed_at": datetime.now(timezone.utc).isoformat(),
            "locked_at": None, "error": None, "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", str(task["id"])).eq("user_id", user_id).execute()
        if run_id:
            db.table("office_agent_runs").update({
                "status": "succeeded", "output": output, "duration_ms": duration,
                "finished_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", run_id).execute()
        return {"status": "succeeded", "task_id": task["id"], "agent": agent, "result": output}
    except Exception as exc:
        duration = int((time.monotonic() - started) * 1000)
        if run_id:
            db.table("office_agent_runs").update({
                "status": "failed", "error": str(exc)[:3000], "duration_ms": duration,
                "finished_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", run_id).execute()
        raise
