from __future__ import annotations

from pathlib import Path

try:
    from tools.apply_writes import (
        ALLOWED_ROOT_FILES,
        ALLOWED_WRITE_PREFIXES,
        DENIED_WRITE_PATHS,
        PLACEHOLDER_WRITE_PATHS,
    )
except ModuleNotFoundError:
    from apply_writes import (  # type: ignore
        ALLOWED_ROOT_FILES,
        ALLOWED_WRITE_PREFIXES,
        DENIED_WRITE_PATHS,
        PLACEHOLDER_WRITE_PATHS,
    )

_ALLOWED_PREFIXES_STR = ', '.join(sorted(ALLOWED_WRITE_PREFIXES))
_ALLOWED_ROOT_STR = ', '.join(sorted(ALLOWED_ROOT_FILES))
_DENIED_STR = ', '.join(sorted(DENIED_WRITE_PATHS))
_PLACEHOLDER_STR = ', '.join(sorted(PLACEHOLDER_WRITE_PATHS))
_AGENTS_MD_PATH = Path(__file__).resolve().parents[1] / 'AGENTS.md'
_AGENTS_MD = (
    _AGENTS_MD_PATH.read_text(encoding='utf-8') if _AGENTS_MD_PATH.exists() else ''
)

SYSTEM_JSON_WRITES = f"""
Return exactly one valid JSON object matching the required schema.
Do not include markdown fences.
Do not include prose before or after the JSON object.
Do not include comments.
Do not include extra keys.

JSON RULES:
- writes[i].content must contain complete file contents as a valid JSON string.
- JSON escaping must be correct.
- Prefer single-quoted Python strings and docstrings when practical.
- Do NOT use Python triple-double-quoted docstrings.
- Use ONLY single-quoted docstrings with meaningful content.

PYTHON CODING RULES (PEP 8 / Python 3.12):
- Follow PEP 8 strictly.
- Use type hinting for ALL function signatures.
- Prefer pydantic v2 for data validation; asyncio for I/O-bound tasks.
- Use ONLY single-quoted docstrings with meaningful content.
- Use loguru logger — never print().
- Use modern built-in generics and unions.

PATH RULES (ENFORCED BY VALIDATOR — violations will be rejected):
- ALL Python source under src/aetherlink/ — never src/plugins/.
- C++ (.cpp/.h) NEVER inside src/ — use host/ or include/ only.
- Do NOT create new top-level directories.
- Allowed prefixes: {_ALLOWED_PREFIXES_STR}
- Allowed root files: {_ALLOWED_ROOT_STR}
- Forbidden paths (hard block): {_DENIED_STR}
- Forbidden placeholders (hard block): {_PLACEHOLDER_STR}
- All paths must be repository-relative (never absolute).
"""

IMPL_SYSTEM = SYSTEM_JSON_WRITES + (
    f'\n\n# PROJECT RULES (AGENTS.md - authoritative)\n{_AGENTS_MD}\n'
    if _AGENTS_MD
    else ''
)

SYSTEM_PM_NEXT = """Return ONLY valid JSON:
{
  "phase": "Phase 0|Phase 1|Phase 2|Phase 3|Phase 4",

  "work_items": [
    {
      "id": "phaseX_slug",
      "title": "short",
      "agent": "architect|ui-ux",
      "acceptance": ["testable bullets"],
      "notes": "short"
    }
  ]
}
Rules:
- Choose the earliest phase not completed.
- Pick 1 work item (exactly ONE).
- Item MUST be explicitly listed in PLAN.md under that phase.
- The "title" must exactly match one PLAN.md bullet from that phase.
- Acceptance criteria must only measure completion of that single selected item.
- Do not use phase-wide exit criteria or global KPI targets
  unless explicitly part of the selected item text.
- For contract/proto/ABI use architect; for Qt shell/panels use ui-ux.
No extra keys. No markdown.
"""

SYSTEM_PM_VERIFY = """
Return ONLY valid JSON:

{"status":"pass|fail","missing":["..."],"notes":"short"}
Rules:
- Evaluate ONLY the explicit acceptance list in the provided work item payload.
- Do not require unrelated phase exit criteria, global KPIs, or future milestone items.
- If acceptance is empty, return fail and explain what is missing.
- No extra keys. No markdown.
"""
