"""Core abstraction for dynamic Python plugins in Aetherlink."""

from __future__ import annotations

from abc import ABC, abstractmethod


class PluginInterface(ABC):
    """Abstract base class mirroring the C-ABI plugin lifecycle contract."""

    @abstractmethod
    def initialize(self) -> None:
        """Initialize the plugin."""

    @abstractmethod
    def start(self) -> None:
        """Start the plugin."""

    @abstractmethod
    def stop(self) -> None:
        """Stop the plugin."""

    @abstractmethod
    def shutdown(self) -> None:
        """Shutdown the plugin."""

    @abstractmethod
    def get_capabilities(self) -> dict:
        """Return plugin capabilities."""

    @abstractmethod
    def required_entitlements(self) -> list:
        """Return required entitlements."""

    @abstractmethod
    def requires_worker(self) -> bool:
        """Return whether the plugin requires a worker."""
