"""Plugin loader module for Aetherlink."""

import importlib

from loguru import logger

from .plugin_interface import PluginInterface


class PluginLoadError(Exception):
    """Raised when a plugin fails to load."""


class PluginLoader:
    """Loads and validates PluginInterface subclasses by module path."""

    def __init__(self, abi_version: int = 1) -> None:
        """Initialize the loader with the expected ABI version.

        Args:
            abi_version: The host ABI version plugins must match.

        """
        self._abi_version = abi_version
        self._logger = logger.bind(name='PluginLoader')

    def load_plugin(self, module_path: str) -> type[PluginInterface]:
        """Load and validate a plugin class from a module path.

        Args:
            module_path: Dotted module path containing a Plugin class.

        Returns:
            The validated PluginInterface subclass.

        Raises:
            PluginLoadError: If the module is missing, unsigned, or ABI incompatible.

        """
        try:
            module = importlib.import_module(module_path)
        except (ModuleNotFoundError, ImportError) as exc:
            raise PluginLoadError(f'Failed to load plugin: {module_path!r}') from exc

        plugin_class = getattr(module, 'Plugin', None)
        if plugin_class is None:
            raise PluginLoadError(f'No Plugin class found in {module_path!r}')

        plugin_version = getattr(plugin_class, 'api_version', None)
        if plugin_version != self._abi_version:
            raise PluginLoadError(
                f'ABI version mismatch: expected {self._abi_version}, '
                f'got {plugin_version!r}'
            )

        self._logger.debug(f'Loaded plugin: {module_path}')
        return plugin_class
