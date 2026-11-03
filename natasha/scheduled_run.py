from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone

from supabase import create_client

from natasha.worker import claim_one, get_db, process_job
import httpx

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("natasha-scheduler")

USER_ID = os.environ["NATASHA_USER_ID"]
PRODUCT = "Varia Vision"
TARGET_MARKET = "Global"
IDEAL_CUSTOMER = (
    "AgTech companies, drone service providers, crop monitoring platforms, "
    "and agricultural technology providers that could use weed detection, "
    "crop classification, or field-image computer vision."
)
MAX_COMPANIES = 5
DRAIN_WINDOW_SECONDS = max(60, int(os.getenv("DRAIN_WINDOW_SECONDS", "600")))


def enqueue_scheduled_run(db) -> str:
    now = datetime.now(timezone.utc)
    slot = now.strftime("%Y%m%dT%H00Z")
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

    remaining = (
        db.table("natasha_jobs")
        .select("id,status,attempts,last_error")
        .eq("id", job_id)
        .limit(1)
        .execute()
    )
    logger.info("Scheduled mission final state: %s", remaining.data or "not found")


if __name__ == "__main__":
    main()
