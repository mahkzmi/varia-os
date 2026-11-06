from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone

import httpx

from natasha.worker import claim_one, get_db, process_job

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("natasha-scheduler")

USER_ID = os.environ["NATASHA_USER_ID"]
PRODUCT = "Varia Vision"
TARGET_MARKET = "Global"
IDEAL_CUSTOMER = (
    "Prioritize agricultural drone/aerial-imagery providers, crop-scouting and "
    "agronomy service businesses using field imagery. Secondarily identify "
    "AgTech/crop-monitoring platforms with evidenced imagery workflows and "
    "plausible integration gaps, then agricultural equipment/robotics/precision-"
    "weeding businesses where complementary integration is credible. Exclude "
    "generic AI vendors, annotation platforms, directories, investors, research "
    "institutions, and direct competitors unless evidence shows a specific buyer "
    "need or credible partnership path. A high fit score is not qualification."
)
MAX_COMPANIES = 5
DRAIN_WINDOW_SECONDS = max(60, int(os.getenv("DRAIN_WINDOW_SECONDS", "600")))


def enqueue_scheduled_run(db) -> str:
    now = datetime.now(timezone.utc)
    slot_hour = (now.hour // 8) * 8
    slot = now.replace(hour=slot_hour, minute=0, second=0, microsecond=0).strftime("%Y%m%dT%H00Z")
    idempotency_key = f"scheduled-vision-{USER_ID}-{slot}"
    payload = {
        "product": PRODUCT,
        "target_market": TARGET_MARKET,
        "ideal_customer": IDEAL_CUSTOMER,
        "max_companies": MAX_COMPANIES,
    }

    existing = (
        db.table("natasha_jobs")
        .select("id,status")
        .eq("user_id", USER_ID)
        .eq("idempotency_key", idempotency_key)
        .limit(1)
        .execute()
    )
    if existing.data:
        job = existing.data[0]
        logger.info(
            "Scheduled slot already exists: job=%s status=%s",
            job["id"],
            job["status"],
        )
        return job["id"]

    created = (
        db.table("natasha_jobs")
        .insert({
            "user_id": USER_ID,
            "job_type": "agent_run",
            "payload": payload,
            "idempotency_key": idempotency_key,
            "status": "queued",
        })
        .execute()
    )
    if not created.data:
        raise RuntimeError("Supabase did not return the scheduled job")
    job_id = created.data[0]["id"]
    logger.info("Enqueued scheduled Natasha mission: %s", job_id)
    return job_id


def main() -> None:
    db = get_db()
    job_id = enqueue_scheduled_run(db)
    api_url = os.getenv(
        "NATASHA_API_URL", "https://natasha-api.onrender.com"
    ).rstrip("/")
    deadline = time.monotonic() + DRAIN_WINDOW_SECONDS
    logger.info("Scheduled run started for job=%s; API=%s", job_id, api_url)

    with httpx.Client(timeout=httpx.Timeout(180.0, connect=20.0)) as client:
        while time.monotonic() < deadline:
            job = claim_one(db)
            if not job:
                break
            process_job(db, job, client)
            if job.get("id") == job_id:
                break

    remaining = (
        db.table("natasha_jobs")
        .select("id,status,attempts,last_error")
        .eq("id", job_id)
        .limit(1)
        .execute()
    )
    final_state = remaining.data[0] if remaining.data else None
    logger.info("Scheduled mission final state: %s", final_state or "not found")
    if not final_state or final_state.get("status") != "succeeded":
        status = final_state.get("status") if final_state else "missing"
        error = final_state.get("last_error") if final_state else "job not found"
        raise RuntimeError(
            f"Natasha scheduled mission did not succeed: status={status}; error={error}"
        )


if __name__ == "__main__":
    main()
