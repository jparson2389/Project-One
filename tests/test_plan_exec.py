from __future__ import annotations

import subprocess
from types import SimpleNamespace

import tools.plan_exec as plan_exec
import tools.validation_gate as validation_gate


class _ContextMonitorStub:
    def track_usage(
        self, model_alias: str, prompt_tokens: int, context_window: int
    ) -> bool:
        return True


class _GateLayerStub:
    def model_dump(self) -> dict[str, object]:
        return {"name": "physical", "errors": []}


def test_main_skips_impl_after_physical_gate_passes(tmp_path, monkeypatch) -> None:
    root = tmp_path
    (root / "agent_manifest.json").write_text(
        '{"base_url": "http://example.test", "api_key": "test"}',
        encoding="utf-8",
    )
    (root / "PLAN.md").write_text("# plan", encoding="utf-8")
    (root / "PRD.md").write_text("# prd", encoding="utf-8")

    monkeypatch.setattr(plan_exec, "ROOT", root)
    monkeypatch.setattr(plan_exec, "ContextMonitor", _ContextMonitorStub)
    monkeypatch.setattr(plan_exec, "OpenAI", lambda **_: object())
    monkeypatch.setattr(plan_exec, "extract_plan_phase_summary", lambda *_: "plan")
    monkeypatch.setattr(plan_exec, "extract_prd_hard_requirements", lambda *_: "prd")
    monkeypatch.setattr(
        plan_exec,
        "extract_phase_work_items",
        lambda _plan: [
            {
                "id": "phase_0__task",
                "phase": "Phase 0",
                "title": "Task",
                "status": "open",
                "instructions": (
                    "**Target File:** `src/aetherlink/example.py`\n"
                    "**Validation:** `uv run pytest tests/test_example.py -vv`"
                ),
            }
        ],
    )

    state = {
        "items": [
            {
                "id": "phase_0__task",
                "phase": "Phase 0",
                "title": "Task",
                "status": "open",
                "instructions": (
                    "**Target File:** `src/aetherlink/example.py`\n"
                    "**Validation:** `uv run pytest tests/test_example.py -vv`"
                ),
            }
        ],
        "history": [],
    }

    monkeypatch.setattr(
        plan_exec, "load_or_initialize_plan_state", lambda _items: state
    )
    monkeypatch.setattr(
        plan_exec, "next_open_work_items", lambda _state: ("Phase 0", state["items"])
    )
    monkeypatch.setattr(
        plan_exec, "filter_acceptance_criteria", lambda _title, raw: raw
    )
    monkeypatch.setattr(plan_exec, "update_state_item", lambda *args, **kwargs: None)
    monkeypatch.setattr(plan_exec, "save_plan_state", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(plan_exec, "append_history", lambda *args, **kwargs: None)
    monkeypatch.setattr(plan_exec, "count_tokens", lambda _text: 10)
    monkeypatch.setattr(
        plan_exec, "get_model_settings", lambda _model: {"context_window": 16384}
    )
    monkeypatch.setattr(plan_exec, "validate_writes_payload", lambda _payload: None)
    monkeypatch.setattr(
        plan_exec,
        "apply_writes_relpaths",
        lambda _payload: ["src/aetherlink/example.py"],
    )
    monkeypatch.setattr(plan_exec, "run_ps", lambda *_args, **_kwargs: (0, "ok"))
    monkeypatch.setattr(
        subprocess, "run", lambda *args, **kwargs: SimpleNamespace(returncode=0)
    )
    monkeypatch.setattr(
        validation_gate,
        "run_validation_gate",
        lambda **_kwargs: SimpleNamespace(all_passed=True, layers=[_GateLayerStub()]),
    )

    stages: list[str] = []
    verify_prompts: list[str] = []
    pm_verify_calls = 0

    def _fake_call_json_with_retry(**kwargs):
        nonlocal pm_verify_calls
        stage = kwargs["stage"]
        stages.append(stage)
        if stage == "pm_next":
            return {
                "phase": "Phase 0",
                "work_items": [
                    {
                        "id": "phase_0__task",
                        "title": "Task",
                        "agent": "architect",
                        "acceptance": ["Ship the feature"],
                        "notes": "",
                    }
                ],
            }
        if stage == "impl_architect":
            return {
                "writes": [
                    {
                        "path": "src/aetherlink/example.py",
                        "content": (
                            "def feature() -> int:\n"
                            "    '''Return a value.'''\n"
                            "    return 1\n"
                        ),
                    }
                ],
                "notes": "implemented",
            }
        if stage == "pm_verify":
            pm_verify_calls += 1
            verify_prompts.append(kwargs["user"])
            if pm_verify_calls == 1:
                return {
                    "status": "fail",
                    "missing": ["Need clearer evidence"],
                    "notes": "Recheck semantic completeness.",
                }
            return {"status": "pass", "missing": [], "notes": "Looks good."}
        raise AssertionError(f"Unexpected stage: {stage}")

    monkeypatch.setattr(plan_exec, "call_json_with_retry", _fake_call_json_with_retry)

    result = plan_exec.main([])

    assert result == 0
    assert stages == ["pm_next", "impl_architect", "pm_verify", "pm_verify"]
    assert "Recheck semantic completeness." in verify_prompts[1]
