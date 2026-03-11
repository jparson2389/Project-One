"""Tests for tools.gbnf_grammars — grammar constants and backend detection."""

from __future__ import annotations

import json

import tools.plan_exec as plan_exec
from tools.gbnf_grammars import (
    GBNF_PM_NEXT,
    GBNF_PM_VERIFY,
    GBNF_WRITES,
    is_local_backend,
)
from tools.json_utils import PM_NEXT_RESPONSE_FORMAT

# ---------------------------------------------------------------------------
# is_local_backend
# ---------------------------------------------------------------------------


def test_local_backend_localhost() -> None:
    assert is_local_backend('http://localhost:8080/v1') is True


def test_local_backend_127() -> None:
    assert is_local_backend('http://127.0.0.1:8080/v1') is True


def test_local_backend_0000() -> None:
    assert is_local_backend('http://0.0.0.0:8080/v1') is True


def test_remote_backend_openai() -> None:
    assert is_local_backend('https://api.openai.com/v1') is False


def test_remote_backend_custom() -> None:
    assert is_local_backend('https://my-proxy.example.com/v1') is False


def test_local_backend_case_insensitive() -> None:
    assert is_local_backend('http://LOCALHOST:8080/v1') is True


# ---------------------------------------------------------------------------
# Grammar string sanity checks
# ---------------------------------------------------------------------------


def test_gbnf_writes_contains_required_rules() -> None:
    assert 'root' in GBNF_WRITES
    assert 'writes-key' in GBNF_WRITES
    assert 'notes-key' in GBNF_WRITES
    assert 'write-entry' in GBNF_WRITES
    assert 'path-key' in GBNF_WRITES
    assert 'content-key' in GBNF_WRITES
    assert 'string' in GBNF_WRITES


def test_gbnf_pm_next_contains_required_rules() -> None:
    assert 'root' in GBNF_PM_NEXT
    assert 'phase-key' in GBNF_PM_NEXT
    assert 'wi-key' in GBNF_PM_NEXT
    assert 'wi-item' in GBNF_PM_NEXT
    assert 'agent-val' in GBNF_PM_NEXT
    assert 'architect' in GBNF_PM_NEXT
    assert 'ui-ux' in GBNF_PM_NEXT


def test_gbnf_pm_next_requires_exactly_one_item() -> None:
    assert '( space "," space wi-item )*' not in GBNF_PM_NEXT


def test_gbnf_pm_verify_contains_required_rules() -> None:
    assert 'root' in GBNF_PM_VERIFY
    assert 'status-key' in GBNF_PM_VERIFY
    assert 'status-val' in GBNF_PM_VERIFY
    assert 'missing-key' in GBNF_PM_VERIFY
    assert 'notes-key' in GBNF_PM_VERIFY
    assert 'pass' in GBNF_PM_VERIFY
    assert 'fail' in GBNF_PM_VERIFY


def test_gbnf_pm_verify_allows_empty_missing() -> None:
    """The missing array grammar must allow an empty list."""
    assert '"[" space "]"' in GBNF_PM_VERIFY or '[]' in GBNF_PM_VERIFY


# ---------------------------------------------------------------------------
# Validate that known-good payloads match the grammar structure
# (structural check — actual GBNF parsing requires llama.cpp)
# ---------------------------------------------------------------------------


def _valid_writes_payload() -> dict:
    return {
        'writes': [
            {
                'path': 'src/aetherlink/ui/main_window.py',
                'content': 'class MainWindow: ...',
            }
        ],
        'notes': 'Added main window stub',
    }


def _valid_pm_next_payload() -> dict:
    return {
        'phase': 'Phase 1',
        'work_items': [
            {
                'id': 'phase_1__deliver_pyside6_qt_shell',
                'title': 'Deliver PySide6 Qt shell',
                'agent': 'ui-ux',
                'acceptance': ['MainWindow instantiates without error'],
                'notes': 'First UI task',
            }
        ],
    }


def _valid_pm_verify_payload() -> dict:
    return {'status': 'pass', 'missing': [], 'notes': 'All criteria met.'}


def test_valid_writes_payload_is_parseable_json() -> None:
    payload = _valid_writes_payload()
    raw = json.dumps(payload)
    parsed = json.loads(raw)
    assert 'writes' in parsed
    assert 'notes' in parsed
    assert isinstance(parsed['writes'], list)
    assert len(parsed['writes']) >= 1
    assert 'path' in parsed['writes'][0]
    assert 'content' in parsed['writes'][0]


def test_valid_pm_next_payload_is_parseable_json() -> None:
    payload = _valid_pm_next_payload()
    raw = json.dumps(payload)
    parsed = json.loads(raw)
    assert 'phase' in parsed
    assert 'work_items' in parsed
    item = parsed['work_items'][0]
    assert item['agent'] in ('architect', 'ui-ux')


def test_valid_pm_verify_payload_is_parseable_json() -> None:
    payload = _valid_pm_verify_payload()
    raw = json.dumps(payload)
    parsed = json.loads(raw)
    assert parsed['status'] in ('pass', 'fail')
    assert isinstance(parsed['missing'], list)
    assert 'notes' in parsed


# ---------------------------------------------------------------------------
# Grammar integration with call() — verify grammar is threaded correctly
# ---------------------------------------------------------------------------


def test_call_uses_grammar_for_local_backend(monkeypatch) -> None:
    """When grammar is provided and backend is local, extra_body is set."""
    captured_kwargs: dict = {}

    class _FakeClient:
        base_url = 'http://127.0.0.1:8080/v1'

        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    captured_kwargs.update(kwargs)

                    class _Choice:
                        class message:
                            content = '{"test": true}'

                    return type(
                        '_Resp',
                        (),
                        {
                            'model': 'test-model',
                            'choices': [_Choice()],
                        },
                    )()

    plan_exec.call(
        client=_FakeClient(),  # type: ignore
        model='test',
        system='sys',
        user='usr',
        grammar_capable=True,
        grammar='root ::= string',
        response_format={'type': 'json_schema'},
    )
    assert 'extra_body' in captured_kwargs
    assert captured_kwargs['extra_body']['grammar'] == 'root ::= string'
    assert 'response_format' not in captured_kwargs


def test_call_uses_response_format_for_remote_backend(monkeypatch) -> None:
    """When backend is remote, response_format is used and grammar is ignored."""
    captured_kwargs: dict = {}

    class _FakeClient:
        base_url = 'https://api.openai.com/v1'

        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    captured_kwargs.update(kwargs)

                    class _Choice:
                        class message:
                            content = '{"test": true}'

                    return type(
                        '_Resp',
                        (),
                        {
                            'model': 'gpt-4',
                            'choices': [_Choice()],
                        },
                    )()

    plan_exec.call(
        client=_FakeClient(),  # type: ignore
        model='test',
        system='sys',
        user='usr',
        grammar_capable=False,
        grammar='root ::= string',
        response_format={'type': 'json_schema'},
    )
    assert 'response_format' in captured_kwargs
    assert 'extra_body' not in captured_kwargs


def test_pm_next_response_format_requires_single_item() -> None:
    schema = PM_NEXT_RESPONSE_FORMAT['json_schema']['schema']
    item_schema = schema['properties']['work_items']['items']

    assert schema['required'] == ['phase', 'work_items']
    assert schema['additionalProperties'] is False
    assert schema['properties']['work_items']['minItems'] == 1
    assert schema['properties']['work_items']['maxItems'] == 1
    assert item_schema['required'] == ['id', 'title', 'agent', 'acceptance', 'notes']
    assert item_schema['additionalProperties'] is False
    assert item_schema['properties']['agent']['enum'] == ['architect', 'ui-ux']
    assert item_schema['properties']['acceptance']['minItems'] == 1


def test_is_grammar_capable_defaults_true_for_local_url() -> None:
    manifest = plan_exec.AgentManifest(
        base_url='http://127.0.0.1:8080/v1',
        api_key='test',
    )

    assert plan_exec.is_grammar_capable(manifest) is True


def test_is_grammar_capable_defaults_false_for_remote_url() -> None:
    manifest = plan_exec.AgentManifest(
        base_url='https://api.openai.com/v1',
        api_key='test',
    )

    assert plan_exec.is_grammar_capable(manifest) is False


def test_is_grammar_capable_explicit_true_overrides_remote_url() -> None:
    manifest = plan_exec.AgentManifest(
        base_url='https://proxy.example.com/v1',
        api_key='test',
        grammar_capable=True,
    )

    assert plan_exec.is_grammar_capable(manifest) is True


def test_is_grammar_capable_explicit_false_overrides_local_url() -> None:
    manifest = plan_exec.AgentManifest(
        base_url='http://localhost:8080/v1',
        api_key='test',
        grammar_capable=False,
    )

    assert plan_exec.is_grammar_capable(manifest) is False
