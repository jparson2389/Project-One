"""
Three-layer completion gate.
Layer 1: filesystem existence
Layer 2: validation command from PLAN.md instructions
Layer 3: LLM semantic review (existing pm_verify)
"""

from __future__ import annotations

import io
import re
import subprocess
import tokenize
from dataclasses import field
from pathlib import Path

from pydantic import BaseModel, model_validator


def normalize_docstring_quotes(content: str) -> str:
    '''Convert triple-double-quoted STRING tokens to triple-single-quoted.

    Only transforms tokens delimited by """. Never modifies existing
    triple-single-quoted strings or raw text. Skips tokens whose inner
    content contains triple-single-quotes to avoid corruption.
    '''
    if '"""' not in content:
        return content
    lines = content.splitlines(keepends=True)
    if not lines:
        return content

    def offset(pos: tuple[int, int]) -> int:
        line, col = pos
        return sum(len(lines[i]) for i in range(line - 1)) + col

    result: list[str] = []
    last_end = 0
    try:
        for tok in tokenize.generate_tokens(io.StringIO(content).readline):
            start_off = offset(tok.start)
            end_off = offset(tok.end)
            if tok.type == tokenize.STRING and tok.string.startswith('"""'):
                inner = tok.string[3:-3]
                if "'''" in inner:
                    result.append(content[last_end:end_off])
                else:
                    result.append(content[last_end:start_off])
                    result.append("'''" + inner + "'''")
            else:
                result.append(content[last_end:end_off])
            last_end = end_off
        result.append(content[last_end:])
    except tokenize.TokenError:
        return content
    return ''.join(result)


class WriteEntry(BaseModel):
    path: str
    content: str

    @model_validator(mode='after')
    def normalize_py_docstrings(self) -> WriteEntry:
        """Transform triple-double-quoted docstrings to triple-single in .py."""
        if self.path.endswith('.py') and '"""' in self.content:
            self.content = normalize_docstring_quotes(self.content)
        return self


class WritesPayload(BaseModel):
    writes: list[WriteEntry]
    notes: str


# ── Data models (Pydantic v2) ────────────────────────────────────────────────


class GateResult(BaseModel):
    """Result from a single validation gate layer."""

    layer: int
    passed: bool
    evidence: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class ValidationReport(BaseModel):
    """Aggregated result from all validation layers."""

    all_passed: bool
    layers: list[GateResult]
    changed_files: list[str]
    validation_command: str | None = None


# ── Layer 1: Filesystem existence ────────────────────────────────────────────

_TARGET_FILE_RE = re.compile(
    r'\*\*Target Files?:\*\*\s*`([^`]+)`',
    re.IGNORECASE,
)


def extract_target_files(instructions: str) -> list[str]:
    """Parse all **Target File:** paths from a PLAN.md instruction block."""
    return _TARGET_FILE_RE.findall(instructions)


def check_filesystem_existence(
    repo_root: Path,
    instructions: str,
    changed_files: list[str],
) -> GateResult:
    """
    Layer 1 gate: verify every Target File listed in instructions physically
    exists on disk. Also accepts any file present in changed_files.
    """
    target_paths = extract_target_files(instructions)
    if not target_paths:
        # No explicit targets declared — accept whatever was changed.
        return GateResult(
            layer=1,
            passed=bool(changed_files),
            evidence=changed_files,
            errors=[]
            if changed_files
            else ['No files were written and no Target File declared.'],
        )

    changed_set = {Path(p).as_posix() for p in changed_files}
    errors: list[str] = []
    evidence: list[str] = []

    for rel in target_paths:
        abs_path = repo_root / rel
        if abs_path.exists():
            evidence.append(rel)
        elif Path(rel).as_posix() in changed_set:
            evidence.append(rel)  # was written this run
        else:
            errors.append(f'MISSING: {rel}')

    return GateResult(
        layer=1,
        passed=len(errors) == 0,
        evidence=evidence,
        errors=errors,
    )


# ── Layer 2: Validation command ──────────────────────────────────────────────

_VALIDATION_RE = re.compile(
    r'\*\*Validation:\*\*[^\n]*\n\s*`([^`]+)`',
    re.IGNORECASE | re.DOTALL,
)


def extract_validation_command(instructions: str) -> str | None:
    """Parse the **Validation:** shell command from a PLAN.md instruction block."""
    m = _VALIDATION_RE.search(instructions)
    return m.group(1).strip() if m else None


def run_validation_command(
    repo_root: Path,
    command: str,
    timeout: int = 120,
) -> GateResult:
    """
    Layer 2 gate: execute the declared validation command in the repo root.
    A non-zero exit code is treated as a hard failure.
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        passed = result.returncode == 0
        output = (result.stdout + result.stderr).strip()
        return GateResult(
            layer=2,
            passed=passed,
            evidence=[output[:2000]] if passed else [],
            errors=[] if passed else [output[:2000]],
        )
    except subprocess.TimeoutExpired:
        return GateResult(
            layer=2,
            passed=False,
            errors=[f'Validation command timed out after {timeout}s: {command}'],
        )
    except Exception as exc:
        return GateResult(
            layer=2,
            passed=False,
            errors=[f'Validation command raised exception: {exc}'],
        )


# ── Public entry point ───────────────────────────────────────────────────────


def run_validation_gate(
    repo_root: Path,
    instructions: str,
    changed_files: list[str],
) -> ValidationReport:
    """
    Run all physical validation layers.
    Returns a ValidationReport; caller decides whether to proceed to LLM review.
    """
    layers: list[GateResult] = []

    # Layer 1 — filesystem
    l1 = check_filesystem_existence(repo_root, instructions, changed_files)
    layers.append(l1)
    if not l1.passed:
        return ValidationReport(
            all_passed=False,
            layers=layers,
            changed_files=changed_files,
        )

    # Layer 2 — validation command (optional: if not declared, skip gracefully)
    command = extract_validation_command(instructions)
    if command:
        l2 = run_validation_command(repo_root, command)
        layers.append(l2)
        if not l2.passed:
            return ValidationReport(
                all_passed=False,
                layers=layers,
                changed_files=changed_files,
                validation_command=command,
            )

    return ValidationReport(
        all_passed=True,
        layers=layers,
        changed_files=changed_files,
        validation_command=command,
    )
