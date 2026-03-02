from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger
from openai import OpenAI

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / "state" / "plan_state.json"

# Configure Loguru to write to a specfic logs folder
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)
logger.add(
    LOG_DIR / "plan_execution_{time:YYYY-MM-DD}.log", rotation="1 MB", level="DEBUG"
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

SYSTEM_PM_VERIFY = """
Return ONLY valid JSON:

{"status":"pass|fail","missing":["..."],"notes":"short"}
Rules:
- Evaluate ONLY the explicit acceptance list in the provided work item payload.
- Do not require unrelated phase exit criteria, global KPIs, or future milestone items.
- If acceptance is empty, return fail and explain what is missing.
- No extra keys. No markdown.
"""


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

SCHEMA_JSON_WRITES = """{
  "writes": [{"path": "relative/path", "content": "file contents"}],
  "notes": "short"
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
        validate_writes_payload,
    )
except ModuleNotFoundError:  # pragma: no cover
    from apply_writes import (  # type: ignore
        ALLOWED_ROOT_FILES,
        ALLOWED_WRITE_PREFIXES,
        validate_writes_payload,
    )

try:
    from tools.json_utils import safe_json_from_model  # type: ignore
except ModuleNotFoundError:
    from json_utils import safe_json_from_model  # type: ignore[no-redef]


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


def infer_agent_for_title(title: str) -> str:
    lowered = title.lower()
    if any(token in lowered for token in ("abi", "proto", "contract")):
        return "architect"
    return "ui-ux"


_PHASE_HEADER_RE = re.compile(
    r"^\s*##\s+(?P<phase>Phase\s+\d+)\s+[\u2014\-\u2013]\s+(?P<title>.+?)\s*$",
    re.IGNORECASE,
)
_ITEM_RE = re.compile(r"^\s*-\s*\[(?P<mark>[ xX])\]\s+(?P<title>.+?)\s*$")


def extract_phase_work_items(plan_text: str) -> list[dict[str, Any]]:
    """Parse PLAN.md into structured work items via a line-by-line state machine.

    Tolerates em dash, en dash, and hyphen as phase header separators.
    Captures blockquote (>) instruction lines attached to each checklist item.
    """
    items: list[dict[str, Any]] = []
    current_phase: str = ""
    current_item: dict[str, Any] | None = None
    instruction_lines: list[str] = []

    def _flush_item() -> None:
        if current_item is not None:
            current_item["instructions"] = "\n".join(instruction_lines).strip()
            items.append(current_item)

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
            current_item = {
                "id": work_item_id(current_phase, title),
                "phase": current_phase,
                "title": title,
                "status": "done" if mark == "x" else "open",
                "instructions": "",
            }
            continue

        stripped = raw_line.strip()
        if current_item is not None and stripped.startswith(">"):
            instruction_lines.append(stripped.lstrip(">").strip())
    _flush_item()
    return items


def _normalize_state_item(item: dict[str, Any]) -> dict[str, Any]:
    normalized = {
        "id": str(item.get("id", "")).strip(),
        "phase": str(item.get("phase", "")).strip(),
        "title": str(item.get("title", "")).strip(),
        "status": str(item.get("status", "missing")).strip() or "missing",
        "notes": str(item.get("notes", "")).strip(),
        "updated_at": str(item.get("updated_at", "")).strip() or _now_iso(),
        "missing": [],
        "evidence": [],
    }

    missing = item.get("missing", [])
    if isinstance(missing, list):
        normalized["missing"] = [str(x) for x in missing if str(x).strip()]

    evidence = item.get("evidence", [])
    if isinstance(evidence, list):
        normalized["evidence"] = [str(x) for x in evidence if str(x).strip()]

    return normalized


def save_plan_state(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = _now_iso()
    STATE_PATH.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def load_or_initialize_plan_state(plan_items: list[dict[str, str]]) -> dict[str, Any]:
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
            normalized = _normalize_state_item(entry)
            if normalized["id"]:
                existing_items[normalized["id"]] = normalized

    merged_items: list[dict[str, Any]] = []
    for plan_item in plan_items:
        key = plan_item["id"]
        base = {
            "id": key,
            "phase": plan_item["phase"],
            "title": plan_item["title"],
            "instructions": plan_item["instructions"],
            "status": "missing",
            "notes": "",
            "updated_at": _now_iso(),
            "missing": [],
            "evidence": [],
        }
        if key in existing_items:
            persisted = existing_items[key]
            persisted["phase"] = plan_item["phase"]
            persisted["title"] = plan_item["title"]
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


@dataclass(frozen=True)
class ModelCall:
    requested_model: str
    actual_model: str
    content: str


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
    client: OpenAI, model: str, system: str, user: str, temperature: float | None = None
) -> ModelCall:
    """Invokes the LLM and returns the raw model response."""

    resp = client.chat.completions.create(
        model=model,
        temperature=temperature,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return ModelCall(
        requested_model=model,
        actual_model=(resp.model or "<unknown>"),
        content=(resp.choices[0].message.content or "").strip(),
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
) -> dict[str, Any]:
    initial = call(client, model, system, user, temperature=temperature)
    print(
        f"[llm] stage={stage} requested_alias={initial.requested_model} "
        f"actual_model={initial.actual_model} chars={len(initial.content)}"
    )
    if (
        initial.requested_model == "pm"
        and "deepseek" not in initial.actual_model.lower()
    ):
        print(
            f"[llm] stage={stage} pm_fallback_used=true "
            f"resolved_model={initial.actual_model}"
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
    repaired = call(client, model, system, repair_user, temperature=0.0)
    print(
        f"[llm] stage={stage} retry=1 requested_alias={repaired.requested_model} "
        f"actual_model={repaired.actual_model} chars={len(repaired.content)}"
    )
    if (
        repaired.requested_model == "pm"
        and "deepseek" not in repaired.actual_model.lower()
    ):
        print(
            f"[llm] stage={stage} retry=1 pm_fallback_used=true "
            f"resolved_model={repaired.actual_model}"
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
    client = OpenAI(
        base_url=manifest["base_url"],
        api_key=manifest["api_key"],
        timeout=300,
        default_query={
            "response_format": {
                "type": "json_object",
            },
        },
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
    )

    queued_items = queue.get("work_items", [])
    chosen: dict[str, Any] | None = None
    if (
        isinstance(queued_items, list)
        and queued_items
        and isinstance(queued_items[0], dict)
    ):
        chosen = queued_items[0]

    fallback_choice = open_items[0]
    fallback_title = str(fallback_choice.get("title", "")).strip()
    selected_title = fallback_title
    selected_agent = infer_agent_for_title(fallback_title)
    raw_acceptance: list[Any] = []

    invalid_reason = ""
    queued_phase = str(queue.get("phase", "")).strip()

    if not chosen:
        invalid_reason = "missing_work_item"
    else:
        candidate_title = str(chosen.get("title", "")).strip()
        candidate_agent = str(chosen.get("agent", "")).strip()
        if queued_phase != selected_phase:
            invalid_reason = "phase_mismatch"
        elif candidate_title not in allowed_titles:
            invalid_reason = "title_not_open"
        elif candidate_agent not in {"architect", "ui-ux"}:
            invalid_reason = "invalid_agent"
        else:
            selected_title = candidate_title
            selected_agent = candidate_agent
            candidate_acceptance = chosen.get("acceptance", [])
            if isinstance(candidate_acceptance, list):
                raw_acceptance = candidate_acceptance

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

    for attempt in range(max_retries):
        logger.info(f"--- Implementation attempt {attempt + 1}/{max_retries} ---")

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
            "- Minimal diffs.\n"
            "- Return JSON writes only.\n"
            "- REQUIREMENT: Python 3.12, PEP 8, Ruff 0.9.0 compliant.\n"
            "- REQUIREMENT: Use type hinting for all signatures.\n"
            "- REQUIREMENT: Prefer pydantic v2.12.5, asyncio for I/O.\n"
            "- REQUIREMENT: Write tests using pytest v9.0.2.\n"
            "- PATH RULE: Never write to src/plugins/* (forbidden).\n"
            "- PATH RULE: Use src/aetherlink/plugins/* instead.\n"
            "- JSON RULE: Do NOT use triple double quotes anywhere.\n"
            "- JSON RULE: writes[].content must not contain unescaped double quotes.\n"
            "- JSON RULE: Prefer single quotes in code strings.\n"
        )

        if fix_prompt:
            impl_prompt += f"\nPREVIOUS ATTEMPT FAILED. FIX ISSUES:\n{fix_prompt}\n"

        # FIX 2b: Use explicit router alias
        model_alias = selected_agent

        impl_payload = call_json_with_retry(
            client=client,
            stage=f"impl_{selected_agent}",
            model=model_alias,
            system=SYSTEM_JSON_WRITES,
            user=impl_prompt,
            schema_hint=SCHEMA_JSON_WRITES,
            temperature=None,
        )

        try:
            validate_writes_payload(impl_payload)
        except ValueError as exc:
            if attempt < max_retries - 1:
                logger.warning(f"Attempt {attempt + 1}: Invalid writes payload: {exc}")
                fix_prompt = (
                    "Your JSON writes payload was rejected by path validation.\n"
                    "Rules:\n"
                    f"- Allowed prefixes: {', '.join(ALLOWED_WRITE_PREFIXES)}\n"
                    f"- Allowed root files: {', '.join(sorted(ALLOWED_ROOT_FILES))}\n"
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
        rc, quality_out = run_ps(".cursor/workflows/check-quality.ps1", quality_args)

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
                    system=SYSTEM_JSON_WRITES,
                    user=q_fix_prompt,
                    schema_hint=SCHEMA_JSON_WRITES,
                    temperature=None,
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
            from validation_gate import run_validation_gate  # type: ignore[no-redef]

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
                    "Ensure every Target File listed in the PLAN instructions exists "
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
        # --- LAYER 3: LLM semantic review (only reached after physical gate passes) ---
        verify_payload = {
            "title": selected_title,
            "acceptance": acceptance,
            "changed_files": changed,
            "gate_layers": [layer.model_dump() for layer in gate_report.layers],
        }
        verify_prompt = (
            "The physical validation gate has PASSED "
            "(files exist, test command returned 0).\n"
            "Now evaluate semantic completeness only.\n\n"
            "Rules:\n"
            "- Evaluate ONLY listed acceptance criteria for this work item.\n"
            "- Status is 'pass' only if all criteria are fully met.\n"
            "- If 'fail', list missing items concisely.\n\n"
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
        )
        if verdict.get("status") != "pass":
            missing = verdict.get("missing", [])
            missing_list = (
                [str(x) for x in missing] if isinstance(missing, list) else []
            )
            notes = str(verdict.get("notes", "")).strip()

            if attempt < max_retries - 1:
                logger.warning(f"PM Verify Failed. Notes: {notes}")
                fix_prompt = (
                    f"PM Verification Failed. Notes: {notes}\nMissing:\n"
                    + "\n".join(missing_list)
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

    logger.success(f"Task Done: {selected_title} — all 3 layers passed.")
    update_state_item(
        state,
        selected_item_id,
        status="done",
        notes=str(verdict.get("notes", "")).strip(),
        missing=[],
        evidence=changed,
    )
    save_plan_state(state)
    return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
