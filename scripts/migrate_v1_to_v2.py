#!/usr/bin/env python3
"""Aletheia Core — v1 → v2 Migration Script.

Upgrades an existing SQLite-only deployment to the v2 schema by adding
tenant_id columns and backfilling existing rows with tenant_id='default'.

Usage:
    python scripts/migrate_v1_to_v2.py              # normal run
    python scripts/migrate_v1_to_v2.py --dry-run    # preview without changes

This script is idempotent — safe to run multiple times.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path


# ANSI colour helpers (disabled when piped / non-TTY)
_USE_COLOUR = sys.stdout.isatty()


def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _USE_COLOUR else text


def _green(t: str) -> str:
    return _c("32", t)


def _yellow(t: str) -> str:
    return _c("33", t)


def _red(t: str) -> str:
    return _c("31", t)


def _bold(t: str) -> str:
    return _c("1", t)


def _info(msg: str) -> None:
    print(f"  {_green('[OK]')}   {msg}")


def _skip(msg: str) -> None:
    print(f"  {_yellow('[SKIP]')} {msg}")


def _warn(msg: str) -> None:
    print(f"  {_yellow('[WARN]')} {msg}")


def _err(msg: str) -> None:
    print(f"  {_red('[ERR]')}  {msg}")


# ---------------------------------------------------------------------------
# Migration logic
# ---------------------------------------------------------------------------


def migrate_key_store(db_path: str, *, dry_run: bool = False) -> int:
    """Add tenant_id to api_keys and backfill. Returns rows migrated."""
    if not Path(db_path).exists():
        _skip(f"{db_path} does not exist")
        return 0

    conn = sqlite3.connect(db_path)
    try:
        columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(api_keys)").fetchall()
        }
        needs_column = "tenant_id" not in columns

        if needs_column:
            backfill_count = conn.execute(
                "SELECT COUNT(*) FROM api_keys"
            ).fetchone()[0]
        else:
            backfill_count = conn.execute(
                "SELECT COUNT(*) FROM api_keys "
                "WHERE tenant_id IS NULL OR tenant_id = ''"
            ).fetchone()[0]

        total_rows = conn.execute("SELECT COUNT(*) FROM api_keys").fetchone()[0]
        print(f"     Total rows: {total_rows}")

        if dry_run:
            if needs_column:
                _warn(f"Would add tenant_id column to api_keys")
                _warn(f"Would backfill {backfill_count} rows with tenant_id='default'")
            elif backfill_count:
                _warn(f"Would backfill {backfill_count} rows with tenant_id='default'")
            else:
                _info("All rows already have tenant_id set — no changes needed")
            return backfill_count

        # Add tenant_id column if missing
        if needs_column:
            conn.execute(
                "ALTER TABLE api_keys ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'default'"
            )
            _info(f"Added tenant_id column to api_keys in {db_path}")

        # Backfill any NULL or empty tenant_id
        cursor = conn.execute(
            "UPDATE api_keys SET tenant_id = 'default' "
            "WHERE tenant_id IS NULL OR tenant_id = ''"
        )
        migrated = cursor.rowcount
        if migrated:
            _info(f"Backfilled {migrated} rows with tenant_id='default'")
        else:
            _info("All rows already have tenant_id set")

        # Add tenant index
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_api_keys_tenant ON api_keys(tenant_id)"
        )

        # Schema version table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS _key_schema_version (
                id      INTEGER PRIMARY KEY CHECK (id = 1),
                version INTEGER NOT NULL
            )
        """)
        conn.execute(
            "INSERT OR REPLACE INTO _key_schema_version (id, version) VALUES (1, 3)"
        )
        conn.commit()
        _info("Schema version set to 3")
        return migrated
    except Exception as exc:
        _err(f"Migration failed: {exc}")
        return -1
    finally:
        conn.close()


def migrate_decision_store(db_path: str, *, dry_run: bool = False) -> int:
    """Add tenant_id to decision_tokens and deployment_bundle. Returns rows migrated."""
    if not Path(db_path).exists():
        _skip(f"{db_path} does not exist")
        return 0

    conn = sqlite3.connect(db_path)
    try:
        migrated = 0
        for table in ("decision_tokens", "deployment_bundle"):
            columns = {
                row[1]
                for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
            }
            needs_column = "tenant_id" not in columns

            if needs_column:
                count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            else:
                count = conn.execute(
                    f"SELECT COUNT(*) FROM {table} "
                    f"WHERE tenant_id IS NULL OR tenant_id = ''"
                ).fetchone()[0]

            total = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"     {table}: {total} rows")

            if dry_run:
                if needs_column:
                    _warn(f"Would add tenant_id column to {table}")
                    _warn(f"Would backfill {count} rows")
                elif count:
                    _warn(f"Would backfill {count} rows in {table}")
                else:
                    _info(f"{table} already migrated — no changes needed")
                migrated += count
                continue

            if needs_column:
                conn.execute(
                    f"ALTER TABLE {table} ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'default'"
                )
                _info(f"Added tenant_id column to {table}")

            cursor = conn.execute(
                f"UPDATE {table} SET tenant_id = 'default' "
                f"WHERE tenant_id IS NULL OR tenant_id = ''"
            )
            migrated += cursor.rowcount

        if not dry_run:
            conn.commit()
            if migrated:
                _info(f"Backfilled {migrated} total rows with tenant_id='default'")
            else:
                _info("All decision rows already have tenant_id set")
        return migrated
    except Exception as exc:
        _err(f"Migration failed: {exc}")
        return -1
    finally:
        conn.close()


def _detect_production() -> bool:
    """Heuristic: check if this looks like a production environment."""
    env = os.getenv("ENVIRONMENT", "").lower()
    if env == "production":
        return True
    for path in (
        os.getenv("ALETHEIA_KEYSTORE_PATH", ""),
        os.getenv("ALETHEIA_DECISION_DB_PATH", ""),
    ):
        if path and (path.startswith("/var/") or path.startswith("/opt/") or path.startswith("/mnt/")):
            return True
    return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Aletheia Core — v1 → v2 migration (adds multi-tenancy schema)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without modifying databases",
    )
    args = parser.parse_args()

    print()
    print(_bold("=" * 60))
    print(_bold("  Aletheia Core — v1 → v2 Migration"))
    if args.dry_run:
        print(_yellow("  *** DRY RUN — no changes will be made ***"))
    print(_bold("=" * 60))
    print()

    # Production warning
    if _detect_production():
        print(_red("  ⚠  PRODUCTION ENVIRONMENT DETECTED"))
        print(_red("  ⚠  This migration modifies database schema."))
        print(_red("  ⚠  Ensure you have a backup before proceeding."))
        print()
        if not args.dry_run:
            try:
                answer = input("  Continue? [y/N] ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                answer = ""
            if answer != "y":
                print()
                print("  Aborted.")
                sys.exit(1)
        print()

    key_db = os.getenv("ALETHEIA_KEYSTORE_PATH", "data/keys.db")
    print(f"{_bold('1.')} Migrating key store: {key_db}")
    migrate_key_store(key_db, dry_run=args.dry_run)
    print()

    import tempfile
    decision_db = os.getenv(
        "ALETHEIA_DECISION_DB_PATH",
        os.path.join(tempfile.gettempdir(), "aletheia", "decisions.sqlite3"),
    )
    alt_decision_db = "data/aletheia_decisions.sqlite3"
    step = 2
    for db in (decision_db, alt_decision_db):
        print(f"{_bold(f'{step}.')} Migrating decision store: {db}")
        migrate_decision_store(db, dry_run=args.dry_run)
        print()
        step += 1

    print(_bold("=" * 60))
    if args.dry_run:
        print(_yellow("  DRY RUN complete — no changes were made."))
        print(_yellow("  Run without --dry-run to apply migrations."))
    else:
        print(_green("  Migration complete. Your deployment is now v2-ready."))
    print(_bold("=" * 60))
    print()


if __name__ == "__main__":
    main()
