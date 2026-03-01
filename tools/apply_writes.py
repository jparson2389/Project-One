from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ALLOWED_WRITE_PREFIXES: tuple[str, ...] = (
    "src/aetherlink/",
    "include/",
    "host/",
    "tools/",
    ".cursor/",
    ".github/",
    "proto/",
    "assets/",
    "tests/",
    "docs/",
    "state/",
)

ALLOWED_ROOT_FILES: set[str] = {
    "pyproject.toml",
    "README.md",
}
DENIED_WRITE_PATHS: set[str] = {
    "PLAN.md",
    "PRD.md",
    "docs/plan.md",
    "docs/prd.md",
}

PLACEHOLDER_WRITE_PATHS: set[str] = {
    "relative/path",
    "path/to/file",
    "file contents",
    "your/path/here",
}


def _norm_path(p: str) -> str:
    return p.replace("\\", "/").strip().lstrip("./").lower()


_DENIED_WRITE_PATHS_NORM: set[str] = {_norm_path(p) for p in DENIED_WRITE_PATHS}
_PLACEHOLDER_WRITE_PATHS_NORM: set[str] = {
    _norm_path(p) for p in PLACEHOLDER_WRITE_PATHS
}
_ALLOWED_ROOT_FILES_NORM: set[str] = {_norm_path(p) for p in ALLOWED_ROOT_FILES}
_ALLOWED_PREFIXES_NORM: tuple[str, ...] = tuple(
    _norm_path(p) for p in ALLOWED_WRITE_PREFIXES
)


def is_write_path_allowed(path: str) -> bool:
    raw = path
    p = _norm_path(raw)

    if p in _PLACEHOLDER_WRITE_PATHS_NORM:
        return False
    if p in _DENIED_WRITE_PATHS_NORM:
        return False

    raw_clean = raw.strip().lstrip("./")
    if (
        raw_clean in ALLOWED_ROOT_FILES
        or _norm_path(raw_clean) in _ALLOWED_ROOT_FILES_NORM
    ):
        return True

    return any(p.startswith(prefix) for prefix in _ALLOWED_PREFIXES_NORM)


def validate_writes_payload(payload: dict[str, Any]) -> None:
    writes = payload.get("writes")
    if not isinstance(writes, list):
        raise ValueError("Invalid writes payload: 'writes' must be a list.")

    for idx, item in enumerate(writes):
        if not isinstance(item, dict):
            raise ValueError(
                f"Invalid writes payload at index {idx}: entry is not an object."
            )
        path = item.get("path")
        content = item.get("content")
        if not isinstance(path, str) or not isinstance(content, str):
            raise ValueError(
                f"Invalid writes payload at index {idx}: "
                f"'path' and 'content' must be strings."
            )

        clean_path = path.strip()
        if not clean_path:
            raise ValueError(f"Invalid writes payload at index {idx}: path is empty.")
        if clean_path.startswith(("/", "\\")) or re.match(
            r"^[A-Za-z]:[\\/]", clean_path
        ):
            raise ValueError(
                f"Invalid writes payload at index {idx}: path '{path}' is absolute. "
                "Use repository-relative paths."
            )

        normalized = clean_path.replace("\\", "/").lstrip("./")
        if "/../" in f"/{normalized}/" or normalized in {"..", "."}:
            raise ValueError(
                f"Invalid writes payload at index {idx}: "
                f"path '{path}' contains traversal components."
            )

        if not is_write_path_allowed(clean_path):
            raise ValueError(
                f"Invalid writes payload at index {idx}: path '{path}' is not allowed."
            )

        # Check for triple-quoted strings (docstrings)
        if '"""' in content:
            raise ValueError(
                f"Invalid writes payload at index {idx}: "
                'content contains forbidden triple-quoted docstring ("""). '
                "Use single quotes or omit docstrings entirely."
            )


def _safe_path(repo_root: Path, rel: str) -> Path:
    p = (repo_root / rel).resolve()
    rr = repo_root.resolve()
    if p == rr or rr in p.parents:
        return p
    raise ValueError(f"Refusing to write outside repo root: {rel}")


def apply_writes(repo_root: Path, payload: dict[str, Any]) -> list[Path]:
    validate_writes_payload(payload)
    writes = payload.get("writes", [])

    changed: list[Path] = []
    for w in writes:
        path = str(w.get("path"))
        content = str(w.get("content"))

        target = _safe_path(repo_root, path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        changed.append(target)

    return changed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=".")
    ap.add_argument(
        "--in", dest="infile", default="-", help="JSON file or '-' for stdin"
    )
    args = ap.parse_args()

    repo_root = Path(args.repo_root).resolve()

    if args.infile == "-":
        raw = sys.stdin.read()
    else:
        raw = Path(args.infile).read_text(encoding="utf-8")

    payload = json.loads(raw)
    changed = apply_writes(repo_root, payload)

    for p in changed:
        print(p.relative_to(repo_root))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
