"""Handles discovery and loading of dynamic python plugins."""


class PluginLoader:
    """Responsible for dynamically locating and instantiating plugin modules."""

    def __init__(self, services):
        """Initialize the plugin loader with shared core services."""
        self.services = services

    def load_plugin(self, plugin_path):
        """Load a plugin from a given file path or directory.

        Args:
            plugin_path: Absolute or relative location of the plugin target.

        """
        pass
