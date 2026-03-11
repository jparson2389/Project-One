"""Environment model types used by the core runtime."""

from __future__ import annotations


class EnvironmentModel:
    """Represent a managed Python environment."""

    def __init__(self) -> None:
        """Initialize the environment model."""
        self.id: str | None = None
        self.name: str = ''
