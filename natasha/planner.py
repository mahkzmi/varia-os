from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from supabase import create_client

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("natasha-planner")


def main() -> None:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    db = create_client(url, key)
    today = datetime.now(timezone.utc).date().isoformat()

    rows = (
        db.table("office_settings")
        .select("user_id,autonomy_level,agent_configs")
        .eq("autonomy_level", "high")
        .execute()
        .data or []
    )

    for row in rows:
        config = (row.get("agent_configs") or {}).get("natasha") or {}
        if not config.get("enabled"):
            continue
        user_id = str(row["user_id"])
        idempotency_key = f"natasha-autonomous-cycle:{user_id}:{today}"
        existing = (
            db.table("office_tasks")
            .select("id")
            .eq("user_id", user_id)
            .eq("idempotency_key", idempotency_key)
            .limit(1)
            .execute()
            .data or []
        )
        if existing:
            continue

        task = {
            "user_id": user_id,
            "agent": "natasha",
            "task_type": "autonomous_cycle",
            "title": f"Daily Varia operating cycle — {today}",
            "description": (
                "Review current Varia Studio state, identify the highest-value next actions, "
                "and create a short evidence-led operating plan. Do not claim actions are complete "
                "unless there is a persisted result or source."
            ),
            "payload": {
                "cycle_date_utc": today,
                "max_child_tasks": 4,
                "priority_order": [
                    "qualified Varia Vision buyers and integration partners",
                    "sales follow-up and evidence-backed prospect research",
                    "product credibility and pilot readiness",
                    "founder brand and content",
                    "studio operations"
                ],
                "guardrails": {
                    "max_initial_messages_per_day": 15,
                    "active_hours": "24/7",
                    "external_messages_require_connected_channel": True,
                    "respect_recipient_business_hours": True,
                    "approval_required": [
                        "pricing", "negotiation", "contract",
                        "financial_commitment", "website_change"
                    ],
                    "no_unverified_field_validation_claims": True
                }
            },
            "priority": 5,
            "status": "queued",
            "idempotency_key": idempotency_key,
        }
        db.table("office_tasks").insert(task).execute()
        logger.info("Queued daily autonomous cycle for user %s (%s)", user_id, today)


if __name__ == "__main__":
    main()
