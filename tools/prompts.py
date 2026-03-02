SYSTEM_JSON_WRITES = '''
Return ONLY valid JSON. No markdown fences. No prose. No extra keys.

REQUIRED SCHEMA:
{
  "writes": [{"path": "relative/path", "content": "file contents"}],
  "notes": "short summary"
}

CRITICAL JSON ESCAPING RULES:
- writes[i].content must be a valid JSON string.
- Do NOT include unescaped double quotes (") inside writes[i].content.
- Do NOT use Python triple-double-quoted docstrings (""") — EVER.
- Use ONLY single-quoted docstrings: \'\'\'Google-style docstring.\'\'\'
- If a double quote is required in code, escape it as \\".

PYTHON CODING RULES (PEP 8 / Python 3.12):
- Follow PEP 8 strictly.
- Use type hinting for ALL function signatures.
- Prefer pydantic v2 for data validation; asyncio for I/O-bound tasks.
- Include Google-format single-quoted docstrings for all public functions.
- Use loguru logger — never print().
- Modern unions: int | str not Union[int, str]. list[str] not List[str].

PATH RULES (ENFORCED BY VALIDATOR — violations will be rejected):
- ALL Python source under src/aetherlink/ — never src/plugins/.
- C++ (.cpp/.h) NEVER inside src/ — use host/ or include/ only.
- Do NOT create new top-level directories.
- Allowed prefixes: src/aetherlink/, tests/, tools/, proto/, assets/, docs/, state/
- Forbidden: PLAN.md, PRD.md, .venv/, __pycache__/, relative/path (placeholder)

All writes[].path values MUST be repository-relative (never absolute).
'''
