from __future__ import annotations

import logging
import os
import signal
import time
from datetime import datetime, timedelta, timezone

import httpx
from supabase import Client, create_client

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("natasha-worker")

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_ROLE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
NATASHA_API_URL = os.getenv("NATASHA_API_URL", "https://natasha-api.onrender.com").rstrip("/")
POLL_SECONDS = max(2, int(os.getenv("POLL_SECONDS", "5")))
_shutdown = False


def stop_worker(*_: object) -> None:
    global _shutdown
    logger.info("Shutdown requested; finishing current job before exit.")
    _shutdown = True


signal.signal(signal.SIGTERM, stop_worker)
signal.signal(signal.SIGINT, stop_worker)


def get_db() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


def claim_one(db: Client) -> dict | None:
    result = db.rpc("natasha_claim_jobs", {"p_limit": 1}).execute()
    rows = result.data or []
    return rows[0] if rows else None


def process_job(db: Client, job: dict, client: httpx.Client) -> None:
    job_id = job["id"]
    try:
        if job["job_type"] != "agent_run":
            raise ValueError(f"Unsupported job_type: {job['job_type']}")
        response = client.post(
            f"{NATASHA_API_URL}/internal/agent/run",
            headers={"X-Internal-Key": SUPABASE_SERVICE_ROLE_KEY},
            json={"user_id": job["user_id"], "payload": job["payload"]},
        )
        response.raise_for_status()
        output = response.json()
        db.table("natasha_jobs").update({
            "status": "succeeded",
            "locked_at": None,
            "last_error": None,
        }).eq("id", job_id).execute()
        logger.info("Job %s succeeded: %s", job_id, output.get("leads_created", 0))
    except Exception as exc:
        attempts = int(job.get("attempts") or 1)
        max_attempts = int(job.get("max_attempts") or 5)
        retry = attempts < max_attempts
        delay = min(900, 15 * (2 ** max(0, attempts - 1)))
        update = {
            "status": "queued" if retry else "failed",
            "locked_at": None,
            "last_error": str(exc)[:3000],
        }
        if retry:
            update["run_at"] = (datetime.now(timezone.utc) + timedelta(seconds=delay)).isoformat()
        db.table("natasha_jobs").update(update).eq("id", job_id).execute()
        logger.exception(
            "Job %s failed (attempt %s/%s); retry=%s",
            job_id, attempts, max_attempts, retry,
        )


def main() -> None:
    db = get_db()
    logger.info("Natasha worker online; API=%s", NATASHA_API_URL)
    with httpx.Client(timeout=httpx.Timeout(180.0, connect=15.0)) as client:
        while not _shutdown:
            try:
                job = claim_one(db)
                if job:
                    process_job(db, job, client)
                    continue
            except Exception:
                logger.exception("Worker polling cycle failed")
            for _ in range(POLL_SECONDS):
                if _shutdown:
                    break
                time.sleep(1)
    logger.info("Natasha worker stopped cleanly.")


if __name__ == "__main__":
    main()
