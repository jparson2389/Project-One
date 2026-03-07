from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from loguru import logger
from openai import OpenAI
from pydantic import BaseModel, Field, field_validator

try:
    from tools.json_utils import WRITES_RESPONSE_FORMAT, safe_json_from_model
except ModuleNotFoundError:
    from json_utils import (  # type: ignore[no-redef]
        WRITES_RESPONSE_FORMAT,
        safe_json_from_model,
    )

try:
    from tools.prompts import IMPL_SYSTEM, SYSTEM_PM_NEXT, SYSTEM_PM_VERIFY
except ModuleNotFoundError:
    from prompts import (  # type: ignore[no-redef]
        IMPL_SYSTEM,
        SYSTEM_PM_NEXT,
        SYSTEM_PM_VERIFY,
    )

try:
    from tools.context_utils import ContextMonitor, count_tokens, get_model_settings
except ModuleNotFoundError:
    from context_utils import (  # type: ignore[no-redef]
        ContextMonitor,
        count_tokens,
        get_model_settings,
    )

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / "state" / "plan_state.json"

# Configure Loguru to write to a specfic logs folder
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)
logger.add(
    LOG_DIR / "plan_execution_{time:YYYY-MM-DD}.log", rotation="1 MB", level="DEBUG"
)

SCHEMA_PM_NEXT = """{
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
}"""

SCHEMA_PM_VERIFY = """{
  "status": "pass|fail",
  "missing": ["..."],
  "notes": "short"
}"""
try:
    from tools.apply_writes import (  # type: ignore
        ALLOWED_ROOT_FILES,
        ALLOWED_WRITE_PREFIXES,
        DENIED_WRITE_PATHS,
        PLACEHOLDER_WRITE_PATHS,
        validate_writes_payload,
    )
except ModuleNotFoundError:  # pragma: no cover
    from apply_writes import (  # type: ignore
        ALLOWED_ROOT_FILES,
        ALLOWED_WRITE_PREFIXES,
        DENIED_WRITE_PATHS,
        PLACEHOLDER_WRITE_PATHS,
        validate_writes_payload,
    )

_HINT_PREFIXES = ", ".join(sorted(ALLOWED_WRITE_PREFIXES))
_HINT_ROOT = ", ".join(sorted(ALLOWED_ROOT_FILES))
_HINT_DENIED = ", ".join(sorted(DENIED_WRITE_PATHS))
_HINT_PLACEHOLDER = ", ".join(sorted(PLACEHOLDER_WRITE_PATHS))

_SCHEMA_EXAMPLE = """\
REQUIRED JSON SCHEMA - writes payload:
{
  "writes": [
    {
      "path": "src/aetherlink/<module>/<file>.py",
      "content": "<full file content - single-quoted docstrings only>"
    }
  ],
  "notes": "<one-sentence summary>"
}
"""

SCHEMA_HINT_IMPL = (
    _SCHEMA_EXAMPLE
    + f"""\
HARD RULES:
- Allowed prefixes: {_HINT_PREFIXES}
- Allowed root files: {_HINT_ROOT}
- Forbidden paths (hard block): {_HINT_DENIED}
- Forbidden placeholders (hard block): {_HINT_PLACEHOLDER}
- writes[i].path must NEVER be: src/plugins/*, *.cpp, *.h inside src/
- writes[i].content must NEVER contain triple double-quotes
- Use ONLY single-quoted docstrings with meaningful content.
- All function signatures must include type hints
- All public functions must have a Google-style single-quoted docstring
- All paths must be repository-relative (never absolute).
"""
)


class AgentManifest(BaseModel):
    """Validated manifest for LLM router connection."""

    base_url: str
    api_key: str


class PlanWorkItem(BaseModel):
    """A single work item parsed from PLAN.md."""

    id: str
    phase: str
    title: str
    status: Literal["done", "open"]
    instructions: str = ""


class StateItem(BaseModel):
    """A persisted work item in plan_state.json."""

    id: str
    phase: str
    title: str
    instructions: str = ""
    status: str = "missing"
    notes: str = ""
    updated_at: str = ""
    missing: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)

    @field_validator("missing", "evidence", mode="before")
    @classmethod
    def clean_str_list(cls, v: Any) -> list[str]:
        """Strip and filter empty strings from list fields."""
        if not isinstance(v, list):
            return []
        return [str(x) for x in v if str(x).strip()]

    @field_validator("status", mode="before")
    @classmethod
    def default_missing_status(cls, v: Any) -> str:
        """Fall back to missing if status is blank."""
        return str(v).strip() or "missing"

    @field_validator("updated_at", mode="before")
    @classmethod
    def default_timestamp(cls, v: Any) -> str:
        """Fall back to current time if updated_at is blank."""
        return str(v).strip() or _now_iso()


class PMWorkItem(BaseModel):
    """A single work item returned by the PM agent."""

    id: str
    title: str
    agent: Literal["architect", "ui-ux"]
    acceptance: list[str]
    notes: str


class PMResponse(BaseModel):
    """Full response from the PM next-item selector."""

    phase: str
    work_items: list[PMWorkItem]


class ModelCall(BaseModel):
    """Immutable result from a single LLM call."""

    model_config = {"frozen": True}
    requested_model: str
    actual_model: str
    content: str


class PMVerdict(BaseModel):
    """Verification result returned by the PM verify agent."""

    status: Literal["pass", "fail"]
    missing: list[str]
    notes: str

    @field_validator("missing", mode="before")
    @classmethod
    def clean_missing(cls, v: Any) -> list[str]:
        """Strip and filter empty strings from missing list."""
        if not isinstance(v, list):
            return []
        return [str(x) for x in v if str(x).strip()]


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _slug(value: str) -> str:
    token = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return token or "item"


def work_item_id(phase: str, title: str) -> str:
    return f"{_slug(phase)}__{_slug(title)}"


def phase_number(phase: str) -> int:
    match = re.search(r"phase\s+(\d+)", phase, re.IGNORECASE)
    if not match:
        return 999
    return int(match.group(1))


def infer_agent_from_instructions(instructions: str, title: str) -> str:
    """Derive agent from Target file path in PLAN.md instructions.

    Args:
        instructions: Parsed instruction block for the work item.
        title: Work item title (fallback only).

    Returns:
        'ui-ux' if the target file is under a UI path, else 'architect'.
    """
    match = re.search(r"\*\*Target Files?:\*\s*`([^`]+)`", instructions)
    if match:
        path = match.group(1).lower()
        if "/ui/" in path or "/panels/" in path:
            return "ui-ux"
        return "architect"
    # Fallback: ui-ux for unambiguous UI titles
    return (
        "ui-ux"
        if re.search(r"\bui\b|\bpanel\b|\bdashboard\b", title.lower())
        else "architect"
    )


_PHASE_HEADER_RE = re.compile(
    r"^\s*##\s+(?P<phase>Phase\s+\d+)\s+[\u2014\-\u2013]\s+(?P<title>.+?)\s*$",
    re.IGNORECASE,
)
_ITEM_RE = re.compile(r"^\s*-\s*\[(?P<mark>[ xX])\]\s+(?P<title>.+?)\s*$")


def extract_phase_work_items(plan_text: str) -> list[PlanWorkItem]:
    """Parse PLAN.md into structured work items via a line-by-line state machine.

    Tolerates em dash, en dash, and hyphen as phase header separators.
    Captures blockquote (>) instruction lines attached to each checklist item.
    """
    items: list[PlanWorkItem] = []
    current_phase: str = ""
    current_item: PlanWorkItem | None = None
    instruction_lines: list[str] = []

    def _flush_item() -> None:
        nonlocal current_item
        if current_item is not None:
            items.append(
                current_item.model_copy(
                    update={"instructions": "\n".join(instruction_lines).strip()}
                )
            )

    for raw_line in plan_text.splitlines():
        # Phase header?
        phase_m = _PHASE_HEADER_RE.match(raw_line)
        if phase_m:
            _flush_item()
            current_item = None
            instruction_lines = []
            current_phase = phase_m.group("phase").strip()
            continue
        if not current_phase:
            continue
        # Checklist item?
        item_m = _ITEM_RE.match(raw_line)
        if item_m:
            _flush_item()
            instruction_lines = []
            mark = item_m.group("mark").strip().lower()
            title = item_m.group("title").strip()
            current_item = PlanWorkItem(
                id=work_item_id(current_phase, title),
                phase=current_phase,
                title=title,
                status="done" if mark == "x" else "open",
            )
            continue

        stripped = raw_line.strip()
        if current_item is not None and stripped.startswith(">"):
            instruction_lines.append(stripped.lstrip(">").strip())
    _flush_item()
    return items


def save_plan_state(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = _now_iso()
    STATE_PATH.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def load_or_initialize_plan_state(plan_items: list[PlanWorkItem]) -> dict[str, Any]:
    existing: dict[str, Any] = {}
    if STATE_PATH.exists():
        try:
            existing = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = {}

    existing_items: dict[str, dict[str, Any]] = {}
    raw_items = existing.get("items", [])
    if isinstance(raw_items, list):
        for entry in raw_items:
            if not isinstance(entry, dict):
                continue
            try:
                item = StateItem.model_validate(entry)
                if item.id:
                    existing_items[item.id] = item.model_dump()
            except Exception:
                continue

    merged_items: list[dict[str, Any]] = []
    for plan_item in plan_items:
        key = plan_item.id
        base = {
            "id": key,
            "phase": plan_item.phase,
            "title": plan_item.title,
            "instructions": plan_item.instructions,
            "status": "missing",
            "notes": "",
            "updated_at": _now_iso(),
            "missing": [],
            "evidence": [],
        }
        if key in existing_items:
            persisted = existing_items[key]
            persisted["phase"] = plan_item.phase
            persisted["title"] = plan_item.title
            base.update(persisted)
        merged_items.append(base)

    history = existing.get("history", [])
    if not isinstance(history, list):
        history = []

    if history:
        latest_by_id: dict[str, dict[str, Any]] = {}
        for event in history:
            if not isinstance(event, dict):
                continue
            phase = str(event.get("phase", "")).strip()
            title = str(event.get("title", "")).strip()
            status = str(event.get("status", "")).strip()
            if not phase or not title or not status:
                continue
            item_key = work_item_id(phase, title)
            latest_by_id[item_key] = event

        for item in merged_items:
            item_id = str(item.get("id", ""))
            replay = latest_by_id.get(item_id)
            if not replay:
                continue
            replay_status = str(replay.get("status", "")).strip()
            if replay_status:
                item["status"] = replay_status
            replay_notes = str(replay.get("notes", "")).strip()
            if replay_notes:
                item["notes"] = replay_notes
            replay_missing = replay.get("missing", [])
            if isinstance(replay_missing, list):
                item["missing"] = [str(x) for x in replay_missing if str(x).strip()]
            replay_files = replay.get("changed_files", [])
            if isinstance(replay_files, list):
                item["evidence"] = [str(x) for x in replay_files if str(x).strip()]

    state = {
        "version": 1,
        "updated_at": _now_iso(),
        "items": merged_items,
        "history": history,
    }
    save_plan_state(state)
    return state


def next_open_work_items(
    state: dict[str, Any],
) -> tuple[str, list[dict[str, Any]]]:
    items = state.get("items", [])
    if not isinstance(items, list):
        return "", []

    open_items = [
        item
        for item in items
        if isinstance(item, dict) and item.get("status") != "done"
    ]
    if not open_items:
        return "", []

    phases = [
        str(item.get("phase") or "").strip()
        for item in open_items
        if isinstance(item, dict)
    ]
    phases = [p for p in phases if p]
    if not phases:
        return "", []

    phase = min(phases, key=phase_number)

    phase_items = [
        item
        for item in items
        if isinstance(item, dict)
        and str(item.get("phase") or "").strip() == phase
        and item.get("status") != "done"
    ]
    return phase, phase_items


def update_state_item(
    state: dict[str, Any],
    item_id: str,
    *,
    status: str,
    notes: str = "",
    missing: list[str] | None = None,
    evidence: list[str] | None = None,
) -> None:
    items = state.get("items", [])
    if not isinstance(items, list):
        return

    target: dict[str, Any] | None = None
    for item in items:
        if isinstance(item, dict) and item.get("id") == item_id:
            target = item
            break
    if target is None:
        return

    target["status"] = status
    target["updated_at"] = _now_iso()
    if notes:
        target["notes"] = notes
    if missing is not None:
        target["missing"] = missing
    if evidence is not None:
        target["evidence"] = evidence


def append_history(
    state: dict[str, Any],
    *,
    phase: str,
    title: str,
    status: str,
    changed_files: list[str],
    missing: list[str] | None = None,
    notes: str = "",
) -> None:
    history = state.get("history")
    if not isinstance(history, list):
        history = []
        state["history"] = history

    payload = {
        "timestamp": _now_iso(),
        "phase": phase,
        "title": title,
        "status": status,
        "changed_files": changed_files,
        "missing": missing or [],
        "notes": notes,
    }
    history.append(payload)


def run_ps(path: str, args: list[str] | None = None) -> tuple[int, str]:
    cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(ROOT / path)]
    if args:
        cmd.extend(args)
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out


def apply_writes_relpaths(payload: dict[str, Any]) -> list[str]:
    try:
        from tools.apply_writes import apply_writes as _apply  # local import
    except ModuleNotFoundError:  # pragma: no cover
        from apply_writes import apply_writes as _apply  # type: ignore[no-redef]

    changed = _apply(ROOT, payload)
    return [str(p.relative_to(ROOT)) for p in changed]


def call(
    client: OpenAI,
    model: str,
    system: str,
    user: str,
    temperature: float | None = None,
    response_format: Any = None,
) -> ModelCall:
    """Invokes the LLM and returns the raw model response."""
    kwargs: dict[str, Any] = {
        "model": model,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    if response_format is not None:
        kwargs["response_format"] = response_format

    resp = client.chat.completions.create(**kwargs)

    content = (resp.choices[0].message.content or "").strip()
    return ModelCall(
        requested_model=model,
        actual_model=(resp.model or "<unknown>"),
        content=content,
    )


def _write_failed_response(stage: str, kind: str, raw_text: str) -> Path:
    logs_dir = ROOT / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    target = logs_dir / f"plan_exec_{stage}_{kind}_{stamp}.txt"
    target.write_text(raw_text, encoding="utf-8")
    return target


def call_json_with_retry(
    client: OpenAI,
    stage: str,
    model: str,
    system: str,
    user: str,
    schema_hint: str,
    temperature: float | None = None,  # let the model use its default temperature
    response_format: dict | None = None,
) -> dict[str, Any]:
    from pathlib import Path

    debug_dir = Path("logs")
    debug_dir.mkdir(exist_ok=True)

    safe_stage = stage.replace("/", "_").replace("\\", "_")
    (debug_dir / f"prompt_system_{safe_stage}.txt").write_text(
        system,
        encoding="utf-8",
    )
    (debug_dir / f"prompt_user_{safe_stage}.txt").write_text(
        user,
        encoding="utf-8",
    )
    initial = call(
        client,
        model,
        system,
        user,
        temperature=temperature,
        response_format=response_format,
    )
    logger.debug(
        f"[llm] stage={stage} requested_alias={initial.requested_model} "
        f"actual_model={initial.actual_model} chars={len(initial.content)}"
    )
    if initial.requested_model != initial.actual_model:
        logger.debug(
            f"[llm] stage={stage} alias_resolved "
            f"requested_alias={initial.requested_model} "
            f"actual_model={initial.actual_model}"
        )

    try:
        return safe_json_from_model(stage, initial.content)
    except ValueError:
        first_dump = _write_failed_response(stage, "first", initial.content)

    repair_user = (
        "Your previous response was invalid for this task.\n"
        "Return ONLY valid JSON with no markdown fences and no prose.\n\n"
        f"Required schema:\n{schema_hint}\n\n"
        "Previous response:\n"
        f"{initial.content}"
    )
    (debug_dir / f"prompt_repair_user_{safe_stage}.txt").write_text(
        repair_user,
        encoding="utf-8",
    )
    repaired = call(
        client,
        model,
        system,
        repair_user,
        temperature=None,
        response_format=response_format,
    )
    logger.debug(
        f"[llm] stage={stage} retry=1 requested_alias={repaired.requested_model} "
        f"actual_model={repaired.actual_model} chars={len(repaired.content)}"
    )
    if repaired.requested_model != repaired.actual_model:
        logger.debug(
            f"[llm] stage={stage} retry=1 alias_resolved=true "
            f"requested_alias={repaired.requested_model} "
            f"actual_model={repaired.actual_model}"
        )
    try:
        return safe_json_from_model(stage, repaired.content)
    except ValueError as exc:
        second_dump = _write_failed_response(stage, "retry", repaired.content)
        raise ValueError(
            f"Stage '{stage}' returned invalid JSON twice. "
            f"Saved raw responses to '{first_dump}' and '{second_dump}'."
        ) from exc


def _clip(text: str, max_chars: int) -> str:
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 500] + "\n...\n" + text[-500:]


def _title_keywords(title: str) -> set[str]:
    stop_words = {
        "add",
        "and",
        "deliver",
        "implement",
        "the",
        "with",
    }
    words = re.findall(r"[a-z0-9]+", title.lower())
    return {word for word in words if len(word) >= 3 and word not in stop_words}


def filter_acceptance_criteria(title: str, acceptance: list[Any]) -> list[str]:
    criteria = [
        item.strip() for item in acceptance if isinstance(item, str) and item.strip()
    ]
    if not criteria:
        return [f"Complete PLAN work item: {title}"]

    keywords = _title_keywords(title)
    if not keywords:
        return criteria

    filtered: list[str] = []
    for criterion in criteria:
        text = criterion.lower()
        if any(keyword in text for keyword in keywords):
            filtered.append(criterion)

    if filtered:
        return filtered

    # Fall back to a single scoped criterion rather than phase-wide KPIs.
    return [f"Complete PLAN work item: {title}"]


def quality_scope_args(changed_files: list[str]) -> list[str]:
    unique_paths = [p for p in dict.fromkeys(changed_files) if p.strip()]
    if not unique_paths:
        return []
    return ["-Paths", *unique_paths]


def extract_plan_phase_summary(plan: str, max_chars: int = 12000) -> str:
    """Shrinks PLAN.md while preserving only Phase sections and their tasks."""
    keep: list[str] = []
    for line in plan.splitlines():
        # Check for Phase headers
        if re.match(r"^\s*## Phase", line, re.I):
            keep.append(line)
            continue
        # Check for Exit Criteria
        if re.match(r"^\s*Exit Criteria", line, re.I):
            keep.append(line)
            continue
        # Check for Task items (-) or Instructions (>)
        if re.match(r"^\s*[-\>]", line):
            keep.append(line)
    result_text = "\n".join(keep)
    return result_text[:max_chars]


def extract_prd_hard_requirements(prd: str, max_chars: int = 12000) -> str:
    """Extracts high-signal PRD sections using regex to survive formatting shifts."""
    keep: list[str] = []
    capture = False
    targets = {"architectural", "plugin system", "capture system"}
    for line in prd.splitlines():
        # Regex looks for '##' regardless of leading whitespace
        header_match = re.match(r"^\s*##\s+(.*)$", line)
        if header_match:
            header_content = header_match.group(1).lower()
            # Start capturing if header matches keywords
            capture = any(t in header_content for t in targets)
        if capture:
            keep.append(line)
    # Fallback to whole doc if no specific sections were caught
    result_text = "\n".join(keep) if keep else prd
    return result_text[:max_chars]


def main(argv: list[str] | None = None) -> int:
    """Execute the implementation plan iteratively."""
    ap = argparse.ArgumentParser(prog="tools.plan_exec")
    ap.add_argument("--max-doc-chars", type=int, default=32000)
    ap.add_argument("--state-only", action="store_true")
    ap.add_argument("--plan", default="PLAN.md")
    ap.add_argument("--prd", default="PRD.md")
    ap.add_argument("--manifest", default="agent_manifest.json")
    args = ap.parse_args(argv if argv is not None else sys.argv[1:])
    manifest = json.loads((ROOT / args.manifest).read_text(encoding="utf-8"))
    _ctx_monitor = ContextMonitor()
    client = OpenAI(
        base_url=manifest["base_url"],
        api_key=manifest["api_key"],
        timeout=300,
    )
    plan = (ROOT / args.plan).read_text(encoding="utf-8", errors="ignore")
    prd = (
        (ROOT / args.prd).read_text(encoding="utf-8", errors="ignore")
        if (ROOT / args.prd).exists()
        else ""
    )

    max_doc_chars = args.max_doc_chars

    plan_summary = extract_plan_phase_summary(plan, max_doc_chars)
    prd_summary = extract_prd_hard_requirements(prd, max_doc_chars)

    plan_items = extract_phase_work_items(plan)
    state = load_or_initialize_plan_state(plan_items)
    selected_phase, open_items = next_open_work_items(state)

    if args.state_only:
        return 0

    # 1. Map titles to instructions
    open_items_map = {
        item["title"]: item.get("instructions", "").strip()
        for item in open_items
        if item.get("title")
    }

    # 2. Build the set of allowed titles
    allowed_titles = set(open_items_map.keys())

    allowed_lines = [
        f"- {t}\n  Requirements: {i}" if i else f"- {t}"
        for t, i in open_items_map.items()
    ]
    allowed_text = "\n".join(allowed_lines)

    # 4. Log progress (Concise & PEP 8 compliant)
    done_items = [i for i in state.get("items", []) if i.get("status") == "done"]
    done_count = len(done_items)
    total_count = len(state.get("items", []))

    logger.info(
        f"[state] phase={selected_phase} open={len(open_items)} "
        f"completed={done_count}/{total_count}"
    )

    # 5. Construct the PM Prompt (PEP 8 / 88-char compliant)
    pm_prompt = (
        "You are executing the Implementation Plan strictly in order.\n\n"
        "Deterministic execution state:\n"
        f"- Earliest incomplete phase: {selected_phase}\n"
        "- Allowed unfinished work items (choose one exact title):\n"
        f"{allowed_text}\n\n"
        "Rules:\n"
        "1. You MUST select one title from the list above.\n"
        f"2. Phase MUST be exactly '{selected_phase}'.\n"
        "3. Use the 'Requirements' listed under your chosen title to "
        "define the scope.\n"
        "4. Attach concrete acceptance criteria based on those "
        "specific Requirements.\n\n"
        "Return JSON only.\n\n"
        "PRD excerpt (hard requirements):\n"
        f"{prd_summary}\n\n"
        "PLAN excerpt (phases + bullets + exit criteria):\n"
        f"{plan_summary}\n"
    )

    pm_alias = "pm"
    queue = call_json_with_retry(
        client=client,
        stage="pm_next",
        model=pm_alias,
        system=SYSTEM_PM_NEXT,
        user=pm_prompt,
        schema_hint=SCHEMA_PM_NEXT,
        temperature=None,  # let the model use its default temperature
        response_format={"type": "text"},
    )

    try:
        pm_response = PMResponse.model_validate(queue)
        chosen_item = next(iter(pm_response.work_items), None)
        queued_phase = pm_response.phase
    except Exception:
        chosen_item = None
        queued_phase = ""

    fallback_choice = next(iter(open_items), None)
    if fallback_choice is None:
        logger.error("No open items available.")
        return 1
    fallback_title = str(fallback_choice.get("title", "")).strip()
    selected_title = fallback_title
    selected_agent = infer_agent_from_instructions(
        fallback_choice.get("instructions", ""), fallback_title
    )
    raw_acceptance: list[Any] = []
    invalid_reason = ""

    if not chosen_item:
        invalid_reason = "missing_work_item"
    else:
        if queued_phase != selected_phase:
            invalid_reason = "phase_mismatch"
        elif chosen_item.title not in allowed_titles:
            invalid_reason = "title_not_open"
        else:
            selected_title = chosen_item.title
            selected_agent = chosen_item.agent
            raw_acceptance = chosen_item.acceptance

    if invalid_reason:
        logger.warning(f"[pm_next] invalid_selection={invalid_reason} fallback=true")
        raw_acceptance = [f"Complete PLAN work item: {selected_title}"]

    # Ensure we have the requirements for the final selected title
    selected_requirements = open_items_map.get(
        selected_title, "No specific requirements provided in PLAN.md."
    )

    # --- VERIFICATION PRINT ---
    logger.info("=" * 40)
    logger.info(f"TARGET TASK: {selected_title}")
    logger.info(f"PLAN SPECS: {selected_requirements}")
    logger.info("=" * 40)

    selected_item_id = work_item_id(selected_phase or "unknown", selected_title)
    acceptance = filter_acceptance_criteria(selected_title, raw_acceptance)

    update_state_item(
        state,
        selected_item_id,
        status="in_progress",
        notes="Execution started",
    )
    save_plan_state(state)

    max_retries: int = 3
    fix_prompt: str = ""
    verify_retry_notes: str = ""
    verdict: dict[str, Any] = {}
    changed: list[str] = []
    skip_impl: bool = False
    gate_report = None
    parsed_verdict = PMVerdict.model_validate(
        {"status": "fail", "missing": [], "notes": ""}
    )

    for attempt in range(max_retries):
        logger.info(f"--- Implementation attempt {attempt + 1}/{max_retries} ---")

        if skip_impl:
            logger.info("Physical gate passed - skipping impl, retrying PM verify only")
        else:
            impl_prompt = (
                "Implement this PLAN work item ONLY.\n\n"
                f"Title: {selected_title}\n\n"
                f"Plan Requirements: {selected_requirements}\n\n"
                "Acceptance criteria:\n"
                f"{json.dumps(acceptance, indent=2)}\n\n"
                "PRD excerpt (hard requirements):\n"
                f"{prd_summary}\n\n"
                "Constraints:\n"
                "- Do not implement other PLAN items yet.\n"
                "- Only touch files necessary for this work item.\n"
                "- Minimal diffs.\n"
                "- Write real, working logic only.\n"
                "- No placeholder code.\n"
            )
            if fix_prompt:
                impl_prompt += f"\nPREVIOUS ATTEMPT FAILED. FIX ISSUES:\n{fix_prompt}\n"

            # FIX 2b: Use explicit router alias
            model_alias = selected_agent

            if not _ctx_monitor.track_usage(
                model_alias,
                count_tokens(impl_prompt),
                int(get_model_settings(model_alias).get("context_window", 16384)),
            ):
                logger.warning(
                    f"[context] prompt near limit for {model_alias} - truncating"
                )
                prd_summary = _clip(prd_summary, 4000)
                plan_summary = _clip(plan_summary, 4000)

            impl_payload = call_json_with_retry(
                client=client,
                stage=f"impl_{selected_agent}",
                model=model_alias,
                system=IMPL_SYSTEM,
                user=impl_prompt,
                schema_hint=SCHEMA_HINT_IMPL,
                temperature=None,
                response_format=WRITES_RESPONSE_FORMAT,
            )

            try:
                validate_writes_payload(impl_payload)
            except ValueError as exc:
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Attempt {attempt + 1}: Invalid writes payload: {exc}"
                    )
                    fix_prompt = (
                        "Your JSON writes payload was rejected by path validation.\n"
                        "Rules:\n"
                        f"- Allowed prefixes: {_HINT_PREFIXES}\n"
                        f"- Allowed root files: {_HINT_ROOT}\n"
                        f"- Forbidden paths: {_HINT_DENIED}\n"
                        f"- Forbidden placeholders: {_HINT_PLACEHOLDER}\n"
                        "- Use ONLY single-quoted docstrings with meaningful content.\n"
                        "- All public functions must have single-quoted docstrings.\n"
                        "- Do NOT write to src/plugins/*.\n"
                        "- If you meant a Python package plugin,\n"
                        "- write under src/aetherlink/plugins/.\n"
                        "- If you meant repo-root plugins, write under plugins/.\n"
                        f"Error: {exc}\n"
                        "Return corrected JSON writes only."
                    )
                    continue
                raise

            changed = apply_writes_relpaths(impl_payload)
            if changed:
                import subprocess

                subprocess.run(
                    ["uv", "run", "ruff", "format", *changed],
                    cwd=ROOT,
                    capture_output=True,
                )
            # Hard Gate: refuse to proceed if no files were written.
            if not changed:
                no_write_msg = (
                    "Implementation returned no file writes. "
                    "Return real code, not stubs or comments."
                )
                if attempt < max_retries - 1:
                    logger.warning(f"Attempt {attempt + 1}: {no_write_msg}")
                    fix_prompt = no_write_msg
                    continue
                else:
                    logger.error("Task Blocked: No files written on final attempt.")
                    update_state_item(
                        state,
                        selected_item_id,
                        status="blocked",
                        notes=no_write_msg,
                        missing=["No files written"],
                        evidence=[],
                    )
                    save_plan_state(state)
                    return 1

            logger.info(
                f"Execution Summary | Phase: {selected_phase} | "
                f"Task: {selected_title} | Modified: {len(changed)}"
            )

            build_rc, build_out = run_ps(".cursor/workflows/build-assets.ps1")
            if build_rc != 0:
                if attempt < max_retries - 1:
                    logger.warning(f"Attempt {attempt + 1}: Build failed.")
                    fix_prompt = (
                        "Build assets failed. Fix the build errors:\n"
                        f"{_clip(build_out, 4000)}"
                    )
                    continue
                else:
                    logger.error("Task Blocked: Build failed on final attempt.")
                    update_state_item(
                        state,
                        selected_item_id,
                        status="blocked",
                        notes="Build assets failed",
                        missing=["Build failed"],
                        evidence=changed,
                    )
                    save_plan_state(state)
                    return 1

            quality_args = quality_scope_args(changed)
            rc, quality_out = run_ps(
                ".cursor/workflows/check-quality.ps1", quality_args
            )

            if rc != 0:
                q_out_exc = _clip(quality_out, 12000) if quality_out else ""
                q_fix_prompt = (
                    f"Fix failing quality gate for: {selected_title}\n\n"
                    "Constraints:\n"
                    "- Only modify files listed in Changed files.\n"
                    "- Keep diffs minimal.\n"
                    "- Return strict JSON only (no markdown, no prose).\n"
                    f"Quality command output:\n{q_out_exc}\n\n"
                    f"Changed files:\n{json.dumps(changed, indent=2)}\n\n"
                )

                try:
                    fix_payload = call_json_with_retry(
                        client=client,
                        stage="quick_fix",
                        model="quick-fix",
                        system=IMPL_SYSTEM,
                        user=q_fix_prompt,
                        schema_hint=SCHEMA_HINT_IMPL,
                        temperature=None,
                        response_format=WRITES_RESPONSE_FORMAT,
                    )
                except ValueError as exc:
                    if attempt < max_retries - 1:
                        logger.warning(f"Quick-fix invalid JSON: {exc}. Retrying.")
                        fix_prompt = "Quick-fix invalid JSON. Rewrite code."
                        continue
                    else:
                        logger.error(f"Task Blocked: Bad JSON final attempt: {exc}")
                        update_state_item(
                            state,
                            selected_item_id,
                            status="blocked",
                            notes="Quick-fix invalid JSON",
                            missing=["json"],
                            evidence=changed,
                        )
                        save_plan_state(state)
                        return 1

                validate_writes_payload(fix_payload)
                changed += apply_writes_relpaths(fix_payload)

                rc2, quality_out2 = run_ps(
                    ".cursor/workflows/check-quality.ps1", quality_scope_args(changed)
                )
                if rc2 != 0:
                    if attempt < max_retries - 1:
                        fix_prompt = (
                            "Quality failing after quick fix. Output:\n"
                            f"{_clip(quality_out2, 4000)}"
                        )
                        continue
                    else:
                        logger.error("Task Blocked: Quality failing.")
                        update_state_item(
                            state,
                            selected_item_id,
                            status="blocked",
                            notes="Quality failing",
                            missing=["Quality"],
                            evidence=changed,
                        )
                        save_plan_state(state)
                        return 1

            try:
                from tools.validation_gate import run_validation_gate
            except ModuleNotFoundError:
                from validation_gate import (
                    run_validation_gate,  # type: ignore[no-redef]
                )

            # --- LAYER 1 + 2: Physical gate (filesystem + test command) ---
            gate_report = run_validation_gate(
                repo_root=ROOT,
                instructions=selected_requirements,
                changed_files=changed,
            )
            if not gate_report.all_passed:
                gate_errors = "; ".join(
                    err for layer in gate_report.layers for err in layer.errors
                )
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Physical gate failed (attempt {attempt + 1}): {gate_errors}"
                    )
                    fix_prompt = (
                        f"Physical validation gate failed. Errors:\n{gate_errors}\n\n"
                        "Ensure every Target File listed in the PLAN instructions exists"
                        "in the PLAN instructions exists"
                        "and the **Validation:** command passes."
                    )
                    continue
                else:
                    logger.error("Task Blocked: Physical gate failed on final attempt.")
                    update_state_item(
                        state,
                        selected_item_id,
                        status="blocked",
                        notes=gate_errors,
                        missing=gate_errors.split("; "),
                        evidence=changed,
                    )
                    save_plan_state(state)
                    return 1
        # The physical gate already passed, so retry semantic verification
        # without rerunning implementation on later attempts.
        skip_impl = True

        # --- LAYER 3: LLM semantic review (only reached after physical gate passes) ---
        verify_payload = {
            "title": selected_title,
            "acceptance": acceptance,
            "changed_files": changed,
            "gate_layers": [layer.model_dump() for layer in gate_report.layers]
            if gate_report
            else [],
        }
        verify_prompt = (
            "The physical validation gate has PASSED "
            "(files exist, test command returned 0).\n"
            "Now evaluate semantic completeness only.\n\n"
            "Rules:\n"
            "- Evaluate ONLY listed acceptance criteria for this work item.\n"
            "- Status is 'pass' only if all criteria are fully met.\n"
            "- If 'fail', list missing items concisely.\n\n"
            f"{verify_retry_notes}"
            f"PRD excerpt:\n{prd_summary}\n\n"
            f"PLAN excerpt:\n{plan_summary}\n\n"
            f"Work item:\n{json.dumps(verify_payload, indent=2)}\n"
        )
        verdict = call_json_with_retry(
            client=client,
            stage="pm_verify",
            model="pm",
            system=SYSTEM_PM_VERIFY,
            user=verify_prompt,
            schema_hint=SCHEMA_PM_VERIFY,
            temperature=None,
            response_format={"type": "text"},
        )
        try:
            parsed_verdict = PMVerdict.model_validate(verdict)
        except Exception:
            parsed_verdict = PMVerdict.model_validate(
                {
                    "status": "fail",
                    "missing": [],
                    "notes": "Invalid verdict response",
                }
            )

        if parsed_verdict.status != "pass":
            missing_list = parsed_verdict.missing
            notes = parsed_verdict.notes

            if attempt < max_retries - 1:
                logger.warning(f"PM Verify Failed. Notes: {notes}")
                verify_retry_notes = (
                    "Previous PM verification returned fail.\n"
                    f"Notes: {notes}\n"
                    f"Missing:\n{'\n'.join(missing_list)}\n\n"
                    "Re-evaluate the same changed files against only the listed "
                    "acceptance criteria.\n\n"
                )
                continue
            else:
                logger.error(
                    "Task Partial: PM verify failed after physical gate passed."
                )
                update_state_item(
                    state,
                    selected_item_id,
                    status="partial",
                    notes=notes or "PM verification failed",
                    missing=missing_list,
                    evidence=changed,
                )
                save_plan_state(state)
                return 1
        # All 3 layers passed - exit the retry loop immediately
        break
    logger.success(f"Task Done: {selected_title} — all 3 layers passed.")
    update_state_item(
        state,
        selected_item_id,
        status="done",
        notes=parsed_verdict.notes,
        missing=[],
        evidence=changed,
    )
    append_history(
        state,
        phase=selected_phase,
        title=selected_title,
        status="done",
        changed_files=changed,
        notes=parsed_verdict.notes,
    )
    save_plan_state(state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
