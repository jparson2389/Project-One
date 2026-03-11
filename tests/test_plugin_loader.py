"""Unit tests for the PluginLoader class."""

import unittest
from unittest.mock import MagicMock, patch

from src.aetherlink.plugins.plugin_loader import PluginLoader, PluginLoadError


class TestPluginLoader(unittest.TestCase):
    """Test cases for the PluginLoader class."""

    @patch('src.aetherlink.plugins.plugin_loader.importlib.import_module')
    def test_load_plugin_success(self, mock_import_module):
        """Test loading a plugin successfully."""
        mock_module = MagicMock()
        mock_module.Plugin.api_version = 1
        mock_import_module.return_value = mock_module

        loader = PluginLoader(abi_version=1)
        plugin_class = loader.load_plugin('path.to.plugin')

        self.assertEqual(plugin_class, mock_module.Plugin)

    @patch('src.aetherlink.plugins.plugin_loader.importlib.import_module')
    def test_load_plugin_abi_mismatch(self, mock_import_module):
        """Test loading a plugin with an ABI version mismatch."""
        mock_module = MagicMock()
        mock_module.Plugin.api_version = 2
        mock_import_module.return_value = mock_module

        loader = PluginLoader(abi_version=1)

        with self.assertRaises(PluginLoadError) as context:
            loader.load_plugin('path.to.plugin')

        self.assertIn('ABI version mismatch', str(context.exception))

    @patch('src.aetherlink.plugins.plugin_loader.importlib.import_module')
    def test_load_plugin_import_error(self, mock_import_module):
        """Test loading a plugin with an import error."""
        mock_import_module.side_effect = ModuleNotFoundError()

        loader = PluginLoader(abi_version=1)

        with self.assertRaises(PluginLoadError) as context:
            loader.load_plugin('path.to.plugin')

        self.assertIn('Failed to load plugin', str(context.exception))


if __name__ == '__main__':
    unittest.main()
