from __future__ import annotations

import os
import sys

import httpx


def main() -> int:
    api_url = os.getenv("NATASHA_API_URL", "https://natasha-api.onrender.com").rstrip("/")
    worker_key = os.getenv("WORKER_API_KEY", "")
    if not worker_key:
        raise RuntimeError("WORKER_API_KEY is not configured")

    response = httpx.post(
        f"{api_url}/internal/worker/tick",
        headers={"X-Worker-Key": worker_key},
        timeout=httpx.Timeout(600.0, connect=20.0),
    )
    if response.is_error:
        raise RuntimeError(f"Worker tick failed ({response.status_code}): {response.text[:2000]}")
    print(response.text)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
