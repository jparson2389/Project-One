"""Tests for tools.validation_gate docstring normalization."""

from __future__ import annotations

from tools.validation_gate import (
    WritesPayload,
    normalize_docstring_quotes,
)


def test_normalize_docstring_quotes_simple() -> None:
    """Triple-double-quoted docstring is converted to triple-single."""
    content = 'def foo():\n    """Summary."""\n    pass\n'
    result = normalize_docstring_quotes(content)
    assert "'''Summary.'''" in result
    assert '"""' not in result


def test_normalize_docstring_quotes_preserves_single_quoted() -> None:
    """Existing triple-single-quoted docstrings are left unchanged."""
    content = "def foo():\n    '''Already correct.'''\n    pass\n"
    result = normalize_docstring_quotes(content)
    assert "'''Already correct.'''" in result
    assert content == result


def test_normalize_docstring_quotes_skips_inner_triple_single() -> None:
    """Tokens with triple-single inside are not transformed."""
    content = '"""He said \'\'\'hi\'\'\'"""\n'
    result = normalize_docstring_quotes(content)
    assert '"""' in result
    assert "'''" in result


def test_write_entry_normalizes_py_content() -> None:
    """WriteEntry transforms .py content with triple-double docstrings."""
    payload = WritesPayload(
        writes=[
            {
                'path': 'tests/sample.py',
                'content': 'def bar():\n    """Doc."""\n    return 1\n',
            },
        ],
        notes='',
    )
    entry = payload.writes[0]
    assert "'''Doc.'''" in entry.content
    assert '"""' not in entry.content


def test_write_entry_ignores_non_py() -> None:
    """WriteEntry does not transform non-.py files."""
    payload = WritesPayload(
        writes=[
            {
                'path': 'docs/readme.md',
                'content': 'Some """quoted""" text.\n',
            },
        ],
        notes='',
    )
    entry = payload.writes[0]
    assert '"""quoted"""' in entry.content


def test_apply_writes_uses_transformed_content(tmp_path) -> None:
    """apply_writes persists normalized content from validated model."""
    from tools.apply_writes import apply_writes

    payload = {
        'writes': [
            {
                'path': 'tests/sample_out.py',
                'content': 'def x():\n    """Doc."""\n    pass\n',
            },
        ],
        'notes': '',
    }
    repo = tmp_path / 'repo'
    repo.mkdir()
    (repo / 'tests').mkdir()
    changed = apply_writes(repo, payload)
    assert len(changed) == 1
    written = changed[0].read_text(encoding='utf-8')
    assert "'''Doc.'''" in written
    assert '"""' not in written
