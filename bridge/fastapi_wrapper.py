# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Ashura Joseph Holeyfield - Aletheia Sovereign Systems
"""Compatibility shim: re-exports the FastAPI app from server.app.

Render is configured with startCommand: uvicorn bridge.fastapi_wrapper:app
This module satisfies that import path without duplicating the app.
"""
from server.app import app  # noqa: F401
