#!/usr/bin/env python3
"""Pre-commit hook: verify version strings match across files."""

import json
import pathlib
import re


def main() -> int:
    v_pyproject = re.search(
        r'^version\s*=\s*"([^"]+)"',
        pathlib.Path("pyproject.toml").read_text(),
        re.M,
    ).group(1)

    v_fastapi = re.search(
        r'version\s*=\s*"([^"]+)"',
        pathlib.Path("bridge/fastapi_wrapper.py").read_text(),
    ).group(1)

    v_main = re.search(
        r"v(\d+\.\d+\.\d+)",
        pathlib.Path("main.py").read_text(),
    ).group(1)

    v_pkg = json.loads(pathlib.Path("package.json").read_text())["version"]

    versions = {
        "pyproject.toml": v_pyproject,
        "fastapi_wrapper.py": v_fastapi,
        "main.py": v_main,
        "package.json": v_pkg,
    }
    mismatches = {k: v for k, v in versions.items() if v != v_pyproject}
    if mismatches:
        print(f"Version mismatch: {mismatches} (expected {v_pyproject})")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
