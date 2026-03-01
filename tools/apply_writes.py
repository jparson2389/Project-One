from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def _safe_path(repo_root: Path, rel: str) -> Path:
    p = (repo_root / rel).resolve()
    rr = repo_root.resolve()
    if p == rr or rr in p.parents:
        return p
    raise ValueError(f"Refusing to write outside repo root: {rel}")


def apply_writes(repo_root: Path, payload: dict[str, Any]) -> list[Path]:
    writes = payload.get("writes", [])
    if not isinstance(writes, list):
        raise ValueError("'writes' must be a list")

    changed: list[Path] = []
    for w in writes:
        if not isinstance(w, dict):
            raise ValueError("Each write must be an object")
        path = w.get("path")
        content = w.get("content")
        if not isinstance(path, str) or not isinstance(content, str):
            raise ValueError("Each write requires string 'path' and 'content'")

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
