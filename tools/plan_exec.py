from __future__ import annotations

import json
import re
import subprocess
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

ALLOWED_WRITE_PREFIXES = (
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
    "plan.md",
    "prd.md",
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
    # Normalize Windows/Posix separators + casing for consistent comparisons
    return p.replace("\\", "/").strip().lstrip("./").lower()


_DENIED_WRITE_PATHS_NORM: set[str] = {_norm_path(p) for p in DENIED_WRITE_PATHS}
_PLACEHOLDER_WRITE_PATHS_NORM: set[str] = {
    _norm_path(p) for p in PLACEHOLDER_WRITE_PATHS
}


def is_write_path_allowed(path: str) -> bool:
    raw = path
    p = _norm_path(raw)

    # Block placeholders (case-insensitive)
    if p in _PLACEHOLDER_WRITE_PATHS_NORM:
        return False

    # Block denied paths (case-insensitive)
    if p in _DENIED_WRITE_PATHS_NORM:
        return False

    # Allow explicit root files
    if raw.strip().lstrip("./") in ALLOWED_ROOT_FILES or p in {
        _norm_path(x) for x in ALLOWED_ROOT_FILES
    }:
        return True

    # Allow only under approved prefixes (case-insensitive, normalized)
    prefixes_norm = tuple(_norm_path(x) for x in ALLOWED_WRITE_PREFIXES)
    return any(p.startswith(pref) for pref in prefixes_norm)


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


def extract_phase_work_items(plan_text: str) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    current_phase: str | None = None
    in_milestone_roadmap = False

    for line in plan_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        top_level_heading = re.match(r"^#\s+(.*)$", stripped)
        if top_level_heading:
            heading_text = top_level_heading.group(1).strip().lower()
            in_milestone_roadmap = heading_text == "milestone roadmap"
            if not in_milestone_roadmap:
                current_phase = None

        phase_match = re.match(r"^##\s+(Phase\s+\d+)\b", stripped, re.IGNORECASE)
        if in_milestone_roadmap and phase_match:
            current_phase = f"Phase {phase_match.group(1).split()[-1]}".replace(
                "  ", " "
            ).strip()
            continue

        if stripped.startswith("## ") and not phase_match:
            current_phase = None
            continue

        if not in_milestone_roadmap or not current_phase:
            continue

        if stripped.startswith("Exit Criteria"):
            continue

        if re.fullmatch(r"-{3,}", stripped):
            continue

        if not stripped.startswith("-"):
            continue

        title = stripped[1:].strip()
        if not title or re.fullmatch(r"-{1,}", title):
            continue
        items.append(
            {
                "id": work_item_id(current_phase, title),
                "phase": current_phase,
                "title": title,
            }
        )

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
) -> tuple[str | None, list[dict[str, Any]]]:
    items = state.get("items", [])
    if not isinstance(items, list):
        return None, []

    open_items = [
        item
        for item in items
        if isinstance(item, dict) and item.get("status") != "done"
    ]
    if not open_items:
        return None, []

    phase = min(
        (str(item.get("phase", "")) for item in open_items),
        key=phase_number,
    )
    phase_items = [
        item
        for item in items
        if isinstance(item, dict)
        and str(item.get("phase", "")) == phase
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


def apply_writes(payload: dict[str, Any]) -> list[str]:
    from tools.apply_writes import apply_writes as _apply

    changed = _apply(ROOT, payload)
    return [str(p.relative_to(ROOT)) for p in changed]


def call(
    client: OpenAI, model: str, system: str, user: str, temperature: float = 0.2
) -> ModelCall:
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


def _extract_fenced_json(text: str) -> str | None:
    # Capture the first fenced JSON block when the model wraps output in markdown.
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


def safe_json_from_model(stage: str, raw_text: str) -> dict[str, Any]:
    text = raw_text.strip()
    candidates: list[tuple[str, str]] = []
    if text:
        candidates.append(("direct", text))

    fenced = _extract_fenced_json(text)
    if fenced:
        candidates.append(("fenced", fenced))

    first_obj = _extract_first_json_object(text)
    if first_obj:
        candidates.append(("first_object", first_obj))

    for strategy, candidate in candidates:
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            print(f"[parse] stage={stage} status=ok strategy={strategy}")
            return payload

    print(f"[parse] stage={stage} status=failed")
    raise ValueError(f"Could not parse valid JSON object for stage '{stage}'.")


def call_json_with_retry(
    client: OpenAI,
    stage: str,
    model: str,
    system: str,
    user: str,
    schema_hint: str,
    temperature: float = 0.2,
) -> dict[str, Any]:
    initial = call(client, model, system, user, temperature=temperature)
    print(
        f"[llm] stage={stage} requested_alias={initial.requested_model} "
        f"actual_model={initial.actual_model} chars={len(initial.content)}"
    )
    if (
        initial.requested_model == "pm"
        and "ministral" not in initial.actual_model.lower()
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
        and "ministral" not in repaired.actual_model.lower()
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
                "'path' and 'content' must be strings."
            )

        clean_path = path.strip()
        if not clean_path:
            raise ValueError(f"Invalid writes payload at index {idx}: path is empty.")
        if clean_path.startswith(("/", "\\")) or re.match(
            r"^[A-Za-z]:[\\/]", clean_path
        ):
            raise ValueError(
                f"Invalid writes payload at index {idx}: "
                f"path '{path}' is absolute. Use repository-relative paths."
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
    """Keep only Phase headers, Exit Criteria, and bullet lines.

    This shrinks PLAN.md massively while preserving execution order.
    """
    keep: list[str] = []
    for line in plan.splitlines():
        s = line.strip()
        if s.startswith("## Phase ") or s.startswith("Exit Criteria"):
            keep.append(line)
        elif s.startswith("-"):
            keep.append(line)
    return _clip("\n".join(keep), max_chars)


def extract_prd_hard_requirements(prd: str, max_chars: int = 12000) -> str:
    """Keep only high-signal PRD sections:.

    - 4) Architectural Principles
    - 5.1 Plugin System
    - 5.4 Capture System
    """
    keep: list[str] = []
    capture = False

    for line in prd.splitlines():
        if (
            line.startswith("## 4)")
            or line.startswith("## 5.1")
            or line.startswith("## 5.4")
        ):
            capture = True
        elif line.startswith("## ") and not (
            line.startswith("## 4)")
            or line.startswith("## 5.1")
            or line.startswith("## 5.4")
        ):
            capture = False

        if capture:
            keep.append(line)

    if not keep:
        keep = prd.splitlines()

    return _clip("\n".join(keep), max_chars)


def main() -> int:
    """Execute the implementation plan iteratively."""
    manifest = json.loads((ROOT / "agent_manifest.json").read_text(encoding="utf-8"))
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

    plan = (ROOT / "PLAN.md").read_text(encoding="utf-8", errors="ignore")
    prd = (
        (ROOT / "PRD.md").read_text(encoding="utf-8", errors="ignore")
        if (ROOT / "PRD.md").exists()
        else ""
    )

    # FIX 1: Prevent 18,000+ token context overflow
    max_doc_chars = 32000

    plan_summary = extract_plan_phase_summary(plan, max_doc_chars)
    prd_summary = extract_prd_hard_requirements(prd, max_doc_chars)

    plan_items = extract_phase_work_items(plan)
    state = load_or_initialize_plan_state(plan_items)
    selected_phase, open_items = next_open_work_items(state)

    if not selected_phase or not open_items:
        logger.info("No unfinished PLAN items remain in state.")
        return 0

    allowed_titles = [str(item.get("title", "")).strip() for item in open_items]
    allowed_titles = [title for title in allowed_titles if title]

    done_count = len(
        [
            item
            for item in state.get("items", [])
            if isinstance(item, dict) and item.get("status") == "done"
        ]
    )
    total_count = len(
        [item for item in state.get("items", []) if isinstance(item, dict)]
    )
    logger.info(
        f"[state] phase={selected_phase} open={len(open_items)} "
        f"completed={done_count}/{total_count}"
    )

    allowed_text = "\n".join(f"- {title}" for title in allowed_titles)
    pm_prompt = (
        "You are executing the Implementation Plan strictly in order.\n\n"
        "Deterministic execution state:\n"
        f"- Earliest incomplete phase: {selected_phase}\n"
        "- Allowed unfinished work item titles (choose one exact title):\n"
        f"{allowed_text}\n\n"
        "Rules:\n"
        f"1. You MUST select one title from the list above.\n"
        f"2. Phase MUST be exactly '{selected_phase}'.\n"
        "3. Attach concrete acceptance criteria for only that selected title.\n"
        "4. Do not include phase-wide KPIs unless explicitly in the title.\n\n"
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
        temperature=0.1,
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

    selected_item_id = work_item_id(selected_phase, selected_title)
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
            temperature=0.2,
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

        changed = apply_writes(impl_payload)

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
                    temperature=0.2,
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
            changed += apply_writes(fix_payload)

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

        verify_payload = {
            "title": selected_title,
            "acceptance": acceptance,
            "changed_files": changed,
        }

        verify_prompt = (
            "Verify this work item is complete per PLAN + PRD excerpts.\n\n"
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
            temperature=0.1,
        )

        if verdict.get("status") != "pass":
            missing = verdict.get("missing", [])
            missing_list = (
                [str(x) for x in missing] if isinstance(missing, list) else []
            )
            notes = str(verdict.get("notes", "")).strip()

            if attempt < max_retries - 1:
                missing_str = "\n".join(missing_list)
                logger.warning(f"PM Verify Failed. Notes: {notes}")
                fix_prompt = (
                    f"PM Verification Failed. Notes: {notes}\nMissing:\n{missing_str}"
                )
                continue
            else:
                logger.error("Task Partial: PM verify failed.")
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

        logger.success(f"Task Done: {selected_title} passed PM verification.")
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
