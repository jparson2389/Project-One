from __future__ import annotations

from pathlib import Path

"""Prompt templates for the PM and implementation agents.

This module centralises the system prompts used to instruct the various LLM
agents participating in the implementation plan workflow. Prompts are
declared as module-level constants so they can be reused consistently from
both the main execution loop and tests.  The prompts enforce strict
contracts on the shape of the responses returned by the models.

Changes from upstream:

* The PM next-item selector prompt now requires that the PM select work
  items by their stable `id` rather than by freeform title.  It instructs
  the agent to return exactly one work item whose `id`, `title` and
  `phase` match an open item from the plan state.  Any deviation will be
  rejected by the caller.
* The PM verify prompt has been tightened to allow only the keys
  ``status``, ``missing`` and ``notes``.  A ``pass`` status requires an
  empty ``missing`` list; a ``fail`` status requires at least one item in
  ``missing`` unless the ``notes`` field documents a schema error.  No
  additional commentary or markdown is permitted.
"""

try:
    # Prefer the package version of apply_writes when available.  During
    # testing or fallback execution this package might not be importable,
    # so fall back to a relative import instead.
    from tools.apply_writes import (
        ALLOWED_ROOT_FILES,
        ALLOWED_WRITE_PREFIXES,
        DENIED_WRITE_PATHS,
        PLACEHOLDER_WRITE_PATHS,
    )
except ModuleNotFoundError:  # pragma: no cover
    from apply_writes import (  # type: ignore
        ALLOWED_ROOT_FILES,
        ALLOWED_WRITE_PREFIXES,
        DENIED_WRITE_PATHS,
        PLACEHOLDER_WRITE_PATHS,
    )

_ALLOWED_PREFIXES_STR = ", ".join(sorted(ALLOWED_WRITE_PREFIXES))
_ALLOWED_ROOT_STR = ", ".join(sorted(ALLOWED_ROOT_FILES))
_DENIED_STR = ", ".join(sorted(DENIED_WRITE_PATHS))
_PLACEHOLDER_STR = ", ".join(sorted(PLACEHOLDER_WRITE_PATHS))
_AGENTS_MD_PATH = Path(__file__).resolve().parents[1] / "AGENTS.md"
_AGENTS_MD = (
    _AGENTS_MD_PATH.read_text(encoding="utf-8") if _AGENTS_MD_PATH.exists() else ""
)

# ---------------------------------------------------------------------------
# Implementation agent system prompt
#
# This prompt describes both the JSON serialization contract and a set of
# project-specific coding rules.  It is referenced by the plan executor when
# requesting implementations or quick-fixes from the appropriate agent.
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
 - Docstring example: '''Summary line.''' (never triple-double-quotes)

PYTHON CODING RULES (PEP 8 / Python 3.12):
 - Follow PEP 8 strictly.
- Use type hinting for ALL function signatures.
 - Prefer pydantic v2 for data validation; asyncio for I/O-bound tasks.
 - Use ONLY single-quoted docstrings with meaningful content.
 - Use loguru logger - never print().
 - Use modern built-in generics and unions.

PATH RULES (ENFORCED BY VALIDATOR - violations will be rejected):
 - ALL Python source under src/aetherlink/ - never src/plugins/.
 - C++ (.cpp/.h) NEVER inside src/ - use host/ or include/ only.
 - Do NOT create new top-level directories.
- Allowed prefixes: {_ALLOWED_PREFIXES_STR}
- Allowed root files: {_ALLOWED_ROOT_STR}
- Forbidden paths (hard block): {_DENIED_STR}
- Forbidden placeholders (hard block): {_PLACEHOLDER_STR}
 - All paths must be repository-relative (never absolute).
"""

# Compose the full implementation system prompt.  Append the contents of
# AGENTS.md if present to provide further project context.
IMPL_SYSTEM = SYSTEM_JSON_WRITES + (
    f"\n\n# PROJECT RULES (AGENTS.md - authoritative)\n{_AGENTS_MD}\n" if _AGENTS_MD else ""
)

# ---------------------------------------------------------------------------
# PM next-item selector system prompt
#
# This prompt instructs the PM agent to return exactly one work item from
# the earliest incomplete phase.  The selection must be made by the stable
# identifier (`id`) provided by the plan executor.  The `phase` and
# `title` fields returned must exactly match the corresponding fields in the
# plan state for the chosen `id`.  Deviations or freeform edits will be
# rejected upstream.
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
- Pick exactly ONE work item.
- The returned object's `id` MUST match one open item identifier exactly.
- The `phase` MUST match the phase for that id.
- The `title` MUST exactly match the title associated with the selected id.
- Do not rename or paraphrase the item title.
- Do not invent new identifiers or select closed items.
- Acceptance criteria must measure completion of only the selected item.
 - Do not use phase-wide exit criteria or global KPI targets unless
  explicitly part of the selected item's text.
- For contract/proto/ABI use `architect`; for Qt shell/panels use `ui-ux`.
No extra keys. No markdown.
"""

# ---------------------------------------------------------------------------
# PM verify system prompt
#
# The PM verify prompt instructs the verification agent to judge whether the
# delivered changes satisfy the acceptance criteria for a work item.  The
# response must conform to a simple JSON schema.  A pass requires an
# empty `missing` list; a fail must enumerate at least one missing
# criterion unless there is a schema violation in which case the `notes`
# field should explain.  No additional commentary or markdown is allowed.
SYSTEM_PM_VERIFY = """
Return ONLY valid JSON:

{"status":"pass|fail","missing":["..."],"notes":"short"}
Rules:
- Allowed keys are exactly: `status`, `missing`, `notes`.
- `status` must be either "pass" or "fail".
- A `pass` verdict REQUIRES the `missing` list to be empty.
- A `fail` verdict REQUIRES at least one item in `missing` unless
  the `notes` field explains a schema issue.
- Evaluate ONLY the explicit acceptance list in the provided work item.
- Do not require unrelated phase exit criteria, global KPIs, or future
  milestone items.
- No extra keys. No markdown.
"""
