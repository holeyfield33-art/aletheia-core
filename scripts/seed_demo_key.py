#!/usr/bin/env python3
"""Seed the hosted /demo proxy key into the Aletheia KeyStore.

Background
----------
The Vercel-hosted /api/demo proxy forwards requests to the Render Python
backend with X-API-Key: $ALETHEIA_DEMO_API_KEY. The backend authenticates
that header against its KeyStore (env-var keys were removed in v1.7).

On Render's free tier the filesystem is ephemeral, so a SQLite-backed
KeyStore loses every key on restart. The lifespan startup hook in
``bridge.fastapi_wrapper._seed_demo_key`` already re-imports the configured
demo key on boot — this script is the manual operator equivalent for one-off
re-seeds, dry runs, and Postgres-backed deployments where the key was lost.

Usage
-----
    ALETHEIA_DEMO_API_KEY=sk_trial_xxxxxxxxxxxxxxxxxxxxxxxx \
        python scripts/seed_demo_key.py

    # Fallback (same key via ALETHEIA_API_KEY)
    ALETHEIA_API_KEY=sk_trial_xxxxxxxxxxxxxxxxxxxxxxxx \
        python scripts/seed_demo_key.py

    # Dry run (no writes):
    ALETHEIA_DEMO_API_KEY=... python scripts/seed_demo_key.py --dry-run

The script is idempotent: re-running with the same key is a no-op.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--dry-run", action="store_true", help="Don't write to KeyStore"
    )
    parser.add_argument(
        "--name", default="hosted-demo", help="Key label (default: hosted-demo)"
    )
    parser.add_argument("--plan", default="trial", choices=["trial", "pro", "max"])
    args = parser.parse_args(argv)

    # Make repo importable when invoked directly.
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

    raw_key = os.getenv("ALETHEIA_DEMO_API_KEY", "").strip()
    key_source = "ALETHEIA_DEMO_API_KEY"
    if not raw_key:
        raw_key = os.getenv("ALETHEIA_API_KEY", "").strip()
        key_source = "ALETHEIA_API_KEY"
    if not raw_key:
        print(
            "ERROR: neither ALETHEIA_DEMO_API_KEY nor ALETHEIA_API_KEY is set.",
            file=sys.stderr,
        )
        return 2

    from core.key_store import key_store  # noqa: WPS433 (intentional late import)

    existing = key_store.lookup_by_hash(raw_key)
    if existing is not None:
        print(
            f"KeyStore already contains demo key id={existing.id} prefix={existing.key_prefix}"
        )
        return 0

    if args.dry_run:
        print("DRY RUN: demo key is missing — would import (no write performed).")
        return 0

    record = key_store.import_raw_key(name=args.name, raw_key=raw_key, plan=args.plan)
    print(
        f"Imported demo key from {key_source} id={record.id} "
        f"prefix={record.key_prefix} plan={record.plan}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
