"""Minimal valid plugin for loader tests."""

from __future__ import annotations

from src.aetherlink.plugins.plugin_interface import PluginInterface


class ValidPlugin(PluginInterface):
    """Concrete PluginInterface implementation for testing."""

    def initialize(self) -> None:
        """Initialize the plugin."""

    def start(self) -> None:
        """Start the plugin."""

    def stop(self) -> None:
        """Stop the plugin."""

    def shutdown(self) -> None:
        """Shutdown the plugin."""

    def get_capabilities(self) -> dict:
        """Return plugin capabilities."""
        return {}

    def required_entitlements(self) -> list:
        """Return required entitlements."""
        return []

    def requires_worker(self) -> bool:
        """Return whether the plugin requires a worker."""
        return False
