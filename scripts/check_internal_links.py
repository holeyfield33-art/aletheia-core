#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Ashura Joseph Holeyfield - Aletheia Sovereign Systems
"""Audit internal href targets in app/ TSX files vs actual route files.

Prints a report and exits non-zero if any internal href points at a path
that has no corresponding page.tsx or route.ts.

False-positive exclusions:
  - /api/*      (API routes -- not page routes)
  - /_*         (Next.js internals)
  - mailto:     (handled by href pattern; filtered by leading-slash check)
  - Fragment-only anchors (#section) -- path becomes empty string, skipped
  - /#*         (homepage anchor -- homepage exists)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

APP_DIR = Path("app")
HREF_PATTERN = re.compile(r'href=["\'`](/[a-zA-Z0-9/_\-#?%]*)["\'`]')

# Paths known to be legitimate non-page destinations (external, anchor-only, etc.)
KNOWN_SKIP_PREFIXES = ("/api/", "/_next/", "/_")

# Specific paths that are intentionally external or dynamically handled
EXPLICIT_ALLOWLIST: set[str] = {
    "/",
    "/#services",
    "/#pricing",
}


def existing_routes() -> set[str]:
    routes: set[str] = {"/"}
    for path in APP_DIR.rglob("page.tsx"):
        rel = path.parent.relative_to(APP_DIR)
        route = "/" + str(rel).replace("\\", "/")
        if route in ("/.", "/"):
            route = "/"
        # Strip Next.js route groups like (marketing), (dashboard), etc.
        route = re.sub(r"/\([^)]+\)", "", route)
        if not route:
            route = "/"
        routes.add(route)
    return routes


def main() -> int:
    if not APP_DIR.exists():
        print("ERROR: app/ directory not found. Run from repo root.")
        return 1

    routes = existing_routes()
    broken: list[tuple[Path, str]] = []

    for tsx in APP_DIR.rglob("*.tsx"):
        text = tsx.read_text(encoding="utf-8", errors="ignore")
        for match in HREF_PATTERN.findall(text):
            # Strip query string and fragment for path resolution
            path_only = match.split("?", 1)[0].split("#", 1)[0]
            if not path_only:
                continue

            # Skip known legitimate prefix patterns
            if any(path_only.startswith(p) for p in KNOWN_SKIP_PREFIXES):
                continue

            # Homepage anchor links are fine
            if path_only == "/" or match in EXPLICIT_ALLOWLIST:
                continue

            # Skip dynamic segments like /dashboard/[id]
            if "[" in path_only or "{" in path_only:
                continue

            if path_only in routes:
                continue

            # Try without trailing slash
            if path_only.rstrip("/") in routes:
                continue

            broken.append((tsx, match))

    if broken:
        print("BROKEN INTERNAL LINKS:")
        for f, href in broken:
            print(f"  {f}: {href}")
        return 1

    print(f"OK: {len(routes)} routes checked, no broken internal links found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
