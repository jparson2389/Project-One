"""
Test cases for plugin interface
"""

from src.aetherlink.plugins.plugin_interface import PluginInterface


class DummyPlugin(PluginInterface):
    """A concrete plugin for testing purposes."""

    def initialize(self) -> None:
        pass

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def shutdown(self) -> None:
        pass

    def get_capabilities(self) -> dict:
        return {"test": True}

    def required_entitlements(self) -> list:
        return ["test_entitlement"]

    def requires_worker(self) -> bool:
        return False


class TestPluginInterface:
    def test_get_capabilities(self):
        plugin = DummyPlugin()
        capabilities = plugin.get_capabilities()
        assert isinstance(capabilities, dict)

    def test_required_entitlements(self):
        plugin = DummyPlugin()
        entitlements = plugin.required_entitlements()
        assert isinstance(entitlements, list)

    def test_requires_worker(self):
        plugin = DummyPlugin()
        requires_worker = plugin.requires_worker()
        assert isinstance(requires_worker, bool)
