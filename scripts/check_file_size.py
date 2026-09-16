#!/usr/bin/env python
"""Block files larger than a configured size from being committed.

Run directly or via the pre-commit hook of the same name. Exit code 1 lists
every file over the limit so the author can trim it, move it to LFS, or (in
rare justified cases) skip the hook with an explanatory PR note.
"""

from __future__ import annotations

import sys
from pathlib import Path

MAX_BYTES = 512 * 1024  # 512 KiB


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    excluded = {".git", ".venv", "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache"}
    targets = [Path(arg) for arg in args] or [
        path
        for path in Path(".").rglob("*")
        if path.is_file() and not any(part in excluded for part in path.parts)
    ]
    oversized = [
        (path, path.stat().st_size)
        for path in targets
        if path.is_file() and path.stat().st_size > MAX_BYTES
    ]
    for path, size in sorted(oversized, key=lambda item: -item[1]):
        print(f"OVERSIZE {path}: {size / 1024:.0f} KiB exceeds {MAX_BYTES // 1024} KiB limit")
    if oversized:
        print(
            "Trim the file, move binary assets to Git LFS (.gitattributes), "
            "or discuss in the PR before bypassing this hook."
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
