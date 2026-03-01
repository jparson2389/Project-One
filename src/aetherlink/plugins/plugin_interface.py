"""Abstract plugin interface for runtime-loaded plugins."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class PluginInterface(ABC):
    """Define the minimal lifecycle surface for a plugin."""

    @abstractmethod
    def initialize(self, services: dict[str, Any]) -> None:
        """Initialize the plugin with host-provided services."""

    @abstractmethod
    def start(self, profile: dict[str, Any]) -> None:
        """Start the plugin using a profile/config."""

    @abstractmethod
    def stop(self) -> None:
        """Stop the plugin."""

    @abstractmethod
    def shutdown(self) -> None:
        """Release all plugin resources."""

    @abstractmethod
    def get_capabilities(self) -> dict[str, Any]:
        """Return a capability dictionary for the host."""

    @property
    @abstractmethod
    def required_entitlements(self) -> list[str]:
        """Return required entitlements (license features) for this plugin."""

    @property
    @abstractmethod
    def requires_worker(self) -> bool:
        """Return whether this plugin requires a Python worker process."""
