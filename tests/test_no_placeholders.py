"""Scan src/ and tests/ for placeholder and trivial test patterns."""

from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[1] / "src"
TESTS_ROOT = Path(__file__).resolve().parent

PLACEHOLDER_PATTERNS = [
    "assert True",
    "assert true",
    "pass # TODO",
    "# Add your implementation here",
    "# Placeholder",
    "# TODO: Implement",
]


def test_no_placeholder_code() -> None:
    """Fail if any src/ Python file contains known placeholder patterns."""
    found: list[str] = []
    for py_file in SRC_ROOT.rglob("*.py"):
        text = py_file.read_text(encoding="utf-8", errors="ignore")
        for pattern in PLACEHOLDER_PATTERNS:
            if pattern in text:
                found.append(f"{py_file.relative_to(SRC_ROOT)}: '{pattern}'")
    assert not found, "Placeholder code found in src/:\n" + "\n".join(found)


def test_no_trivial_tests() -> None:
    """Fail if any test file contains trivially passing assertions."""
    found: list[str] = []
    for py_file in TESTS_ROOT.rglob("test_*.py"):
        if py_file == Path(__file__).resolve():
            continue
        text = py_file.read_text(encoding="utf-8", errors="ignore")
        for pattern in ("assert True", "assert true"):
            if pattern in text:
                found.append(f"{py_file.name}: '{pattern}'")
    for py_file in SRC_ROOT.rglob("test_*.py"):
        text = py_file.read_text(encoding="utf-8", errors="ignore")
        for pattern in ("assert True", "assert true"):
            if pattern in text:
                found.append(f"{py_file.relative_to(SRC_ROOT)}: '{pattern}'")
    assert not found, "Trivial tests found:\n" + "\n".join(found)
