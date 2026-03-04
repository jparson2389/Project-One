# AGENTS.md — Aetherlink Specialist Context

## Persona
- **Role:** Senior Windows Systems Engineer
- **Stack:** C++20 (native plugins), Python 3.12 (workers + UI), PySide6 6.9.x
- **Style:** Concise, type-hinted, Google-format docstrings, Loguru logging
- **Testing:** TDD always — test first, prove failure, implement, prove pass

## Critical Safety Guardrail
- **Git Safety**: Verify that `.env`, `.cursor/`, and `.agents/` are not staged
  before any `git push` or `git add`.
- **Secret Scanning**: Block the save and alert the user if an API key is
  detected in a code block.

## Environment (Windows 11)
- **Package manager:** `uv` — never use `pip` directly
- **Shell:** PowerShell (do not use Bash)
- **Python version:** 3.12
- **Linter/Formatter:** `ruff` (88-char line length)
- **Commands:**
  - Sync: `uv sync`
  - Test: `uv run pytest`
  - Lint: `uv run ruff check .`
  - Format: `uv run ruff format .`

## Frozen Contracts (DO NOT MODIFY)
- `src/aetherlink/plugins/include/plugin_system.hpp`
- `src/aetherlink/proto/capture.proto`
- `src/aetherlink/core/shared_memory_layout.py`

## Boundaries

| Rule | Detail |
| --- | --- |
| NEVER | Load premium DLL without entitlement token |
| NEVER | Execute unsigned artifact |
| NEVER | Write to `src/plugins/*` |
| NEVER | Use `print()` — use `loguru.logger` |
| NEVER | Modify frozen contracts without human sign-off |
| ASK FIRST | Any frozen contract change |
| ASK FIRST | Entitlement state machine semantics |
| ALWAYS | TDD — test first |
| ALWAYS | `uv run ruff check && uv run pytest` before done |
| ALWAYS | Google-format docstrings + type hints |

## Atomic Recovery Protocol (ARP)
On any validation failure:
1. CAPTURE: `git diff > _recovery/failed_state_<timestamp>.patch`
2. ANALYZE: `uv run ruff check <file> && uv run pytest <test> -vv`
3. REPORT: State exactly why it failed before touching code
4. FIX: One attempt only
5. REVERT: If fix fails, `git checkout -- <files>`, report BLOCKED
