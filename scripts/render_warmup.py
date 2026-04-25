#!/usr/bin/env python3
"""Warm up a Render-hosted Aletheia backend.

Pings low-cost health/readiness endpoints to reduce cold-start latency
for public demo traffic.
"""

from __future__ import annotations

import os
import sys
import time

import httpx


def _normalize_base(url: str) -> str:
    return url.rstrip("/")


def _get_base_url() -> str:
    base = (
        os.getenv("ALETHEIA_WARMUP_URL")
        or os.getenv("ALETHEIA_BACKEND_URL")
        or os.getenv("ALETHEIA_BASE_URL")
        or "https://aletheia-core.onrender.com"
    ).strip()
    if not base.startswith("http://") and not base.startswith("https://"):
        base = f"https://{base}"
    return _normalize_base(base)


def _ping(url: str, timeout_s: float) -> tuple[bool, int | None, str]:
    try:
        with httpx.Client(timeout=timeout_s, follow_redirects=True) as client:
            resp = client.get(
                url,
                headers={
                    "User-Agent": "aletheia-render-warmup/1.0",
                    "Accept": "application/json,text/plain,*/*",
                },
            )
            # Any HTTP response still wakes the container.
            return (
                True,
                resp.status_code,
                "ok" if resp.is_success else f"http_error:{resp.status_code}",
            )
    except Exception as err:  # pragma: no cover
        return False, None, str(err)


def main() -> int:
    base = _get_base_url()
    timeout_s = float(os.getenv("ALETHEIA_WARMUP_TIMEOUT_SECONDS", "15"))
    delay_s = float(os.getenv("ALETHEIA_WARMUP_DELAY_SECONDS", "1.25"))

    endpoints = [f"{base}/health", f"{base}/ready"]
    print(f"[warmup] base={base}")

    woke_any = False
    for endpoint in endpoints:
        ok, status, detail = _ping(endpoint, timeout_s)
        print(f"[warmup] {endpoint} -> status={status} detail={detail}")
        woke_any = woke_any or ok
        time.sleep(delay_s)

    if not woke_any:
        print("[warmup] failed to reach all endpoints", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
