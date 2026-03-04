"""Ensure no placeholder stubs exist in the src/ tree."""

from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[1] / "src"

PLACEHOLDER_PATTERNS = [
    "pass  # TODO",
    "# Add your implementation here",
    "# Placeholder",
]


def test_no_placeholder_files() -> None:
    """Fail if any src/ Python file contains known placeholder patterns.

    Args:
        None

    Raises:
        AssertionError: If placeholder patterns are found.
    """
    found: list[str] = []
    for py_file in SRC_ROOT.rglob("*.py"):
        text = py_file.read_text(encoding="utf-8", errors="ignore")
        for pattern in PLACEHOLDER_PATTERNS:
            if pattern in text:
                found.append(f"{py_file.relative_to(SRC_ROOT)}: '{pattern}'")
    assert not found, "Placeholder stubs found:\n" + "\n".join(found)
