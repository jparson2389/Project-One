from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

from openai import OpenAI

try:
    from tools.json_utils import parse_json_object
except ModuleNotFoundError:
    from json_utils import parse_json_object  # type: ignore[no-redef]


SYSTEM_JSON_WRITES = '''
Return ONLY valid JSON.

CRITICAL JSON ESCAPING RULES:
- The value of writes[i].content must be a valid JSON string.
- Do NOT include unescaped double quotes (") inside writes[i].content.
- Do NOT use Python triple-double-quoted docstrings (""") anywhere in writes[i].content.
- Prefer single quotes in Python code, or omit docstrings entirely.
- If a double quote is required in code, escape it as \\".

{
  "writes": [{"path": "relative/path", "content": "file contents"}],
  "notes": "short"
}

No markdown fences. No extra keys.
All writes[].path values MUST be repository-relative paths (never absolute).
'''


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8", errors="ignore")


def _extract_fenced_json(text: str) -> str | None:
    match = re.search(
        r"```(?:json)?\s*(\{.*?\})\s*```", text, re.IGNORECASE | re.DOTALL
    )
    if match:
        return match.group(1).strip()
    return None


def _extract_first_json_object(text: str) -> str | None:
    start = -1
    depth = 0
    in_string = False
    escape = False

    for idx, ch in enumerate(text):
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
            continue

        if ch == "{":
            if depth == 0:
                start = idx
            depth += 1
        elif ch == "}" and depth > 0:
            depth -= 1
            if depth == 0 and start >= 0:
                return text[start : idx + 1].strip()

    return None


def _parse_json(s: str) -> dict[str, Any] | None:
    try:
        return parse_json_object(s, stage="agent_call")
    except ValueError:
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--agent", required=True, help="architect|pm|quick-fix|researcher|ui-ux"
    )
    ap.add_argument("--prompt", default=None)
    ap.add_argument("--prompt-file", default=None)
    ap.add_argument("--include", action="append", default=[])
    ap.add_argument("--base-url", default="http://127.0.0.1:4000/v1")
    ap.add_argument("--api-key", default="anything")
    ap.add_argument("--temperature", type=float, default=0.2)
    ap.add_argument("--json-writes", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--repo-root", default=".")

    args = ap.parse_args()

    if not args.prompt and not args.prompt_file:
        print("Provide --prompt or --prompt-file", file=sys.stderr)
        return 2

    prompt = args.prompt or _read(args.prompt_file)

    if args.include:
        ctx = []
        for inc in args.include:
            if Path(inc).exists():
                ctx.append(f"\n\n# FILE: {inc}\n{_read(inc)}")
            else:
                ctx.append(f"\n\n# FILE: {inc}\n<missing>")
        prompt = prompt + "\n" + "\n".join(ctx)

    client = OpenAI(base_url=args.base_url, api_key=args.api_key)

    system = (
        SYSTEM_JSON_WRITES
        if (args.json_writes or args.apply)
        else "Be concise and correct."
    )

    resp = client.chat.completions.create(
        model=args.agent,
        temperature=args.temperature,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    )

    content = (resp.choices[0].message.content or "").strip()

    if not args.apply:
        print(content)
        return 0

    payload = _parse_json(content)
    if payload is None:
        print("Expected JSON but could not parse model output:", file=sys.stderr)
        print(content, file=sys.stderr)
        return 3

    # Apply writes. Support both module invocation (`-m tools.agent_call`)
    # and direct script invocation (`python tools/agent_call.py`).
    try:
        from tools.apply_writes import apply_writes  # local import
    except ModuleNotFoundError:
        from apply_writes import apply_writes  # type: ignore[no-redef]

    repo_root = Path(args.repo_root).resolve()
    changed = apply_writes(repo_root, payload)

    notes = payload.get("notes", "")
    if isinstance(notes, str) and notes:
        print(notes)

    for p in changed:
        print(p.relative_to(repo_root))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
