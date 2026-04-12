"""Shared test fixtures for Aletheia Core test suite."""

from __future__ import annotations

import os

# Auth is disabled for tests by default — existing tests don't supply API keys.
# Individual test classes can override this via patch.dict.
os.environ.setdefault("ALETHEIA_AUTH_DISABLED", "true")
