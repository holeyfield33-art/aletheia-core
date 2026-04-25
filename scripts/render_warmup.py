#!/usr/bin/env python3
"""Warm up a Render-hosted Aletheia backend.

Pings low-cost health/readiness endpoints to reduce cold-start latency
for public demo traffic.
"""

from __future__ import annotations

import os
import sys
import time
import urllib.error
import urllib.request


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
    req = urllib.request.Request(
        url,
        method="GET",
        headers={
            "User-Agent": "aletheia-render-warmup/1.0",
            "Accept": "application/json,text/plain,*/*",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            return True, resp.getcode(), "ok"
    except urllib.error.HTTPError as err:
        # HTTP responses still wake the dyno/container.
        return True, err.code, f"http_error:{err.code}"
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
