from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import sqlite3
import tempfile
import time
from dataclasses import dataclass

import httpx

_logger = logging.getLogger("aletheia.decision_store")

_REDIS_PREFIX = "aletheia:decision:"
_BUNDLE_KEY = "aletheia:policy_bundle"
_DEFAULT_TTL_SECONDS = 3600


def _upstash_configured() -> bool:
    return bool(
        os.getenv("UPSTASH_REDIS_REST_URL", "").strip()
        and os.getenv("UPSTASH_REDIS_REST_TOKEN", "").strip()
    )


@dataclass(frozen=True)
class ReplayCheckResult:
    accepted: bool
    reason: str


class _SQLiteDecisionStore:
    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = db_path or os.getenv(
            "ALETHEIA_DECISION_DB_PATH",
            os.path.join(tempfile.gettempdir(), "aletheia_decisions.sqlite3"),
        )
        self._lock = asyncio.Lock()
        self._init_db()

    @property
    def backend(self) -> str:
        return "sqlite"

    def _init_db(self) -> None:
        conn = sqlite3.connect(self._db_path)
        try:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS decision_tokens (
                    token TEXT PRIMARY KEY,
                    request_id TEXT NOT NULL,
                    issued_at INTEGER NOT NULL,
                    expires_at INTEGER NOT NULL,
                    policy_version TEXT NOT NULL,
                    manifest_hash TEXT NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS deployment_bundle (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    policy_version TEXT NOT NULL,
                    manifest_hash TEXT NOT NULL,
                    updated_at INTEGER NOT NULL
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

    async def claim_token(
        self,
        *,
        token: str,
        request_id: str,
        policy_version: str,
        manifest_hash: str,
        now_ts: int,
        ttl_seconds: int = _DEFAULT_TTL_SECONDS,
    ) -> ReplayCheckResult:
        async with self._lock:
            conn = sqlite3.connect(self._db_path)
            try:
                cur = conn.cursor()
                cur.execute("DELETE FROM decision_tokens WHERE expires_at < ?", (now_ts,))
                try:
                    cur.execute(
                        """
                        INSERT INTO decision_tokens (
                            token, request_id, issued_at, expires_at, policy_version, manifest_hash
                        ) VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            token,
                            request_id,
                            now_ts,
                            now_ts + ttl_seconds,
                            policy_version,
                            manifest_hash,
                        ),
                    )
                except sqlite3.IntegrityError:
                    return ReplayCheckResult(accepted=False, reason="replay_detected")
                conn.commit()
                return ReplayCheckResult(accepted=True, reason="accepted")
            finally:
                conn.close()

    async def verify_bundle(self, *, policy_version: str, manifest_hash: str, now_ts: int) -> ReplayCheckResult:
        async with self._lock:
            conn = sqlite3.connect(self._db_path)
            try:
                cur = conn.cursor()
                row = cur.execute(
                    "SELECT policy_version, manifest_hash FROM deployment_bundle WHERE id = 1"
                ).fetchone()
                if row is None:
                    cur.execute(
                        "INSERT INTO deployment_bundle (id, policy_version, manifest_hash, updated_at) VALUES (1, ?, ?, ?)",
                        (policy_version, manifest_hash, now_ts),
                    )
                    conn.commit()
                    return ReplayCheckResult(accepted=True, reason="bundle_registered")

                existing_version, existing_hash = row
                if existing_version != policy_version or existing_hash != manifest_hash:
                    return ReplayCheckResult(accepted=False, reason="partial_deployment_drift")
                return ReplayCheckResult(accepted=True, reason="bundle_verified")
            finally:
                conn.close()


class _UpstashDecisionStore:
    def __init__(self) -> None:
        self._url = os.getenv("UPSTASH_REDIS_REST_URL", "").rstrip("/")
        self._token = os.getenv("UPSTASH_REDIS_REST_TOKEN", "")
        self._headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    @property
    def backend(self) -> str:
        return "upstash"

    async def _pipeline(self, commands: list[list[str]]) -> list[dict]:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.post(
                f"{self._url}/pipeline",
                headers=self._headers,
                json=commands,
            )
            resp.raise_for_status()
            return resp.json()

    async def claim_token(
        self,
        *,
        token: str,
        request_id: str,
        policy_version: str,
        manifest_hash: str,
        now_ts: int,
        ttl_seconds: int = _DEFAULT_TTL_SECONDS,
    ) -> ReplayCheckResult:
        redis_key = f"{_REDIS_PREFIX}{token}"
        value = json.dumps(
            {
                "request_id": request_id,
                "policy_version": policy_version,
                "manifest_hash": manifest_hash,
                "issued_at": now_ts,
            },
            sort_keys=True,
        )
        payload = [
            ["SET", redis_key, value, "NX", "EX", str(ttl_seconds)],
        ]
        result = await self._pipeline(payload)
        accepted = bool(result and result[0].get("result") == "OK")
        if not accepted:
            return ReplayCheckResult(accepted=False, reason="replay_detected")
        return ReplayCheckResult(accepted=True, reason="accepted")

    async def verify_bundle(self, *, policy_version: str, manifest_hash: str, now_ts: int) -> ReplayCheckResult:
        expected = json.dumps(
            {"policy_version": policy_version, "manifest_hash": manifest_hash},
            sort_keys=True,
        )
        result = await self._pipeline([
            ["SET", _BUNDLE_KEY, expected, "NX", "EX", str(24 * 3600)],
            ["GET", _BUNDLE_KEY],
        ])
        current = ""
        if len(result) > 1:
            current = result[1].get("result") or ""
        if current and current != expected:
            return ReplayCheckResult(accepted=False, reason="partial_deployment_drift")
        return ReplayCheckResult(accepted=True, reason="bundle_verified")


class DecisionStore:
    """Distributed replay and deployment-drift guard with fail-closed degraded mode."""

    def __init__(self) -> None:
        self._central_available = _upstash_configured()
        self._store = _UpstashDecisionStore() if self._central_available else _SQLiteDecisionStore()
        self._degraded = False

    @property
    def backend(self) -> str:
        return self._store.backend

    @property
    def degraded(self) -> bool:
        return self._degraded

    async def verify_policy_bundle(self, policy_version: str, manifest_hash: str) -> ReplayCheckResult:
        now_ts = int(time.time())
        try:
            return await self._store.verify_bundle(
                policy_version=policy_version,
                manifest_hash=manifest_hash,
                now_ts=now_ts,
            )
        except Exception as exc:
            _logger.error("Decision store bundle verification failure: %s", exc)
            self._degraded = True
            return ReplayCheckResult(accepted=False, reason="decision_store_unavailable")

    async def claim_decision(
        self,
        *,
        request_id: str,
        timestamp_iso: str,
        policy_version: str,
        manifest_hash: str,
        ttl_seconds: int = _DEFAULT_TTL_SECONDS,
    ) -> ReplayCheckResult:
        # Deterministic token binding for replay defense.
        token_src = f"{request_id}|{timestamp_iso}|{policy_version}|{manifest_hash}"
        token = hashlib.sha256(token_src.encode("utf-8")).hexdigest()
        now_ts = int(time.time())
        try:
            return await self._store.claim_token(
                token=token,
                request_id=request_id,
                policy_version=policy_version,
                manifest_hash=manifest_hash,
                now_ts=now_ts,
                ttl_seconds=ttl_seconds,
            )
        except Exception as exc:
            _logger.error("Decision store claim failure: %s", exc)
            self._degraded = True
            return ReplayCheckResult(accepted=False, reason="decision_store_unavailable")


decision_store = DecisionStore()
