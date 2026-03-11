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
        return {'name': 'physical', 'errors': []}


def _configure_main_harness(monkeypatch, root) -> None:
    (root / 'agent_manifest.json').write_text(
        '{"base_url": "http://example.test", "api_key": "test"}',
        encoding='utf-8',
    )
    (root / 'PLAN.md').write_text('# plan', encoding='utf-8')
    (root / 'PRD.md').write_text('# prd', encoding='utf-8')

    state = {
        'items': [
            {
                'id': 'phase_0__task',
                'phase': 'Phase 0',
                'title': 'Task',
                'status': 'open',
                'instructions': (
                    '**Target File:** `src/aetherlink/example.py`\n'
                    '**Validation:** `uv run pytest tests/test_example.py -vv`'
                ),
            }
        ],
        'history': [],
    }

    monkeypatch.setattr(plan_exec, 'ROOT', root)
    monkeypatch.setattr(plan_exec, 'ContextMonitor', _ContextMonitorStub)
    monkeypatch.setattr(plan_exec, 'OpenAI', lambda **_: object())
    monkeypatch.setattr(plan_exec, 'extract_plan_phase_summary', lambda *_: 'plan')
    monkeypatch.setattr(plan_exec, 'extract_prd_hard_requirements', lambda *_: 'prd')
    monkeypatch.setattr(
        plan_exec,
        'extract_phase_work_items',
        lambda _plan: [
            {
                'id': 'phase_0__task',
                'phase': 'Phase 0',
                'title': 'Task',
                'status': 'open',
                'instructions': (
                    '**Target File:** `src/aetherlink/example.py`\n'
                    '**Validation:** `uv run pytest tests/test_example.py -vv`'
                ),
            }
        ],
    )
    monkeypatch.setattr(
        plan_exec, 'load_or_initialize_plan_state', lambda _items: state
    )
    monkeypatch.setattr(
        plan_exec, 'next_open_work_items', lambda _state: ('Phase 0', state['items'])
    )
    monkeypatch.setattr(
        plan_exec, 'filter_acceptance_criteria', lambda _title, raw: raw
    )
    monkeypatch.setattr(plan_exec, 'update_state_item', lambda *args, **kwargs: None)
    monkeypatch.setattr(plan_exec, 'save_plan_state', lambda *_args, **_kwargs: None)
    monkeypatch.setattr(plan_exec, 'append_history', lambda *args, **kwargs: None)
    monkeypatch.setattr(plan_exec, 'count_tokens', lambda _text: 10)
    monkeypatch.setattr(
        plan_exec, 'get_model_settings', lambda _model: {'context_window': 16384}
    )
    monkeypatch.setattr(plan_exec, 'validate_writes_payload', lambda _payload: None)
    monkeypatch.setattr(
        plan_exec,
        'apply_writes_relpaths',
        lambda _payload: ['src/aetherlink/example.py'],
    )
    monkeypatch.setattr(
        subprocess, 'run', lambda *args, **kwargs: SimpleNamespace(returncode=0)
    )
    monkeypatch.setattr(
        validation_gate,
        'run_validation_gate',
        lambda **_kwargs: SimpleNamespace(all_passed=True, layers=[_GateLayerStub()]),
    )


def test_main_skips_impl_after_physical_gate_passes(tmp_path, monkeypatch) -> None:
    root = tmp_path
    _configure_main_harness(monkeypatch, root)
    monkeypatch.setattr(plan_exec, 'run_ps', lambda *_args, **_kwargs: (0, 'ok'))

    stages: list[str] = []
    verify_prompts: list[str] = []
    pm_verify_calls = 0

    def _fake_call_json_with_retry(**kwargs):
        nonlocal pm_verify_calls
        stage = kwargs['stage']
        stages.append(stage)
        if stage == 'pm_next':
            return {
                'phase': 'Phase 0',
                'work_items': [
                    {
                        'id': 'phase_0__task',
                        'title': 'Task',
                        'agent': 'architect',
                        'acceptance': ['Ship the feature'],
                        'notes': '',
                    }
                ],
            }
        if stage == 'impl_architect':
            return {
                'writes': [
                    {
                        'path': 'src/aetherlink/example.py',
                        'content': (
                            'def feature() -> int:\n'
                            "    '''Return a value.'''\n"
                            '    return 1\n'
                        ),
                    }
                ],
                'notes': 'implemented',
            }
        if stage == 'pm_verify':
            pm_verify_calls += 1
            verify_prompts.append(kwargs['user'])
            if pm_verify_calls == 1:
                return {
                    'status': 'fail',
                    'missing': ['Need clearer evidence'],
                    'notes': 'Recheck semantic completeness.',
                }
            return {'status': 'pass', 'missing': [], 'notes': 'Looks good.'}
        raise AssertionError(f'Unexpected stage: {stage}')

    monkeypatch.setattr(plan_exec, 'call_json_with_retry', _fake_call_json_with_retry)

    result = plan_exec.main([])

    assert result == 0
    assert stages == ['pm_next', 'impl_architect', 'pm_verify', 'pm_verify']
    assert 'Recheck semantic completeness.' in verify_prompts[1]


def test_main_passes_gbnf_writes_to_quick_fix(tmp_path, monkeypatch) -> None:
    root = tmp_path
    _configure_main_harness(monkeypatch, root)

    quick_fix_kwargs: dict[str, object] = {}

    def _fake_run_ps(path: str, _args=None) -> tuple[int, str]:
        if path == '.cursor/workflows/check-quality.ps1':
            if not _fake_run_ps.seen_quality_failure:  # pyright: ignore[reportFunctionMemberAccess]
                _fake_run_ps.seen_quality_failure = True  # pyright: ignore[reportFunctionMemberAccess]
                return 1, 'quality failed'
        return 0, 'ok'

    _fake_run_ps.seen_quality_failure = False  # pyright: ignore[reportFunctionMemberAccess]
    monkeypatch.setattr(plan_exec, 'run_ps', _fake_run_ps)

    def _fake_call_json_with_retry(**kwargs):
        stage = kwargs['stage']
        if stage == 'pm_next':
            return {
                'phase': 'Phase 0',
                'work_items': [
                    {
                        'id': 'phase_0__task',
                        'title': 'Task',
                        'agent': 'architect',
                        'acceptance': ['Ship the feature'],
                        'notes': '',
                    }
                ],
            }
        if stage == 'impl_architect':
            return {
                'writes': [
                    {
                        'path': 'src/aetherlink/example.py',
                        'content': (
                            'def feature() -> int:\n'
                            "    '''Return a value.'''\n"
                            '    return 1\n'
                        ),
                    }
                ],
                'notes': 'implemented',
            }
        if stage == 'quick_fix':
            quick_fix_kwargs.update(kwargs)
            return {
                'writes': [
                    {
                        'path': 'src/aetherlink/example.py',
                        'content': (
                            'def feature() -> int:\n'
                            "    '''Return a value.'''\n"
                            '    return 2\n'
                        ),
                    }
                ],
                'notes': 'fixed quality',
            }
        if stage == 'pm_verify':
            return {'status': 'pass', 'missing': [], 'notes': 'Looks good.'}
        raise AssertionError(f'Unexpected stage: {stage}')

    monkeypatch.setattr(plan_exec, 'call_json_with_retry', _fake_call_json_with_retry)

    result = plan_exec.main([])

    assert result == 0
    assert quick_fix_kwargs['grammar'] == plan_exec.GBNF_WRITES


def test_main_uses_pm_verify_response_schema(tmp_path, monkeypatch) -> None:
    root = tmp_path
    _configure_main_harness(monkeypatch, root)
    monkeypatch.setattr(plan_exec, 'run_ps', lambda *_args, **_kwargs: (0, 'ok'))

    pm_verify_kwargs: dict[str, object] = {}

    def _fake_call_json_with_retry(**kwargs):
        stage = kwargs['stage']
        if stage == 'pm_next':
            return {
                'phase': 'Phase 0',
                'work_items': [
                    {
                        'id': 'phase_0__task',
                        'title': 'Task',
                        'agent': 'architect',
                        'acceptance': ['Ship the feature'],
                        'notes': '',
                    }
                ],
            }
        if stage == 'impl_architect':
            return {
                'writes': [
                    {
                        'path': 'src/aetherlink/example.py',
                        'content': (
                            'def feature() -> int:\n'
                            "    '''Return a value.'''\n"
                            '    return 1\n'
                        ),
                    }
                ],
                'notes': 'implemented',
            }
        if stage == 'pm_verify':
            pm_verify_kwargs.update(kwargs)
            return {'status': 'pass', 'missing': [], 'notes': 'Looks good.'}
        raise AssertionError(f'Unexpected stage: {stage}')

    monkeypatch.setattr(plan_exec, 'call_json_with_retry', _fake_call_json_with_retry)

    result = plan_exec.main([])

    schema = pm_verify_kwargs['response_format']['json_schema']['schema']  # pyright: ignore[reportIndexIssue]

    assert result == 0
    assert schema['required'] == ['status', 'missing', 'notes']
