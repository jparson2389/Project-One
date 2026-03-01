# src/aetherlink/plugins/plugin.py

class Plugin:
    def __init__(self, plugin_id: str, name: str, version: str, api_version: str, plugin_type: str):
        self.plugin_id = plugin_id
        self.name = name
        self.version = version
        self.api_version = api_version
        self.plugin_type = plugin_type

    def initialize(self, services) -> None:
        pass

    def start(self, profile) -> None:
        pass

    def stop(self) -> None:
        pass

    def shutdown(self) -> None:
        pass

    def get_capabilities(self) -> dict:
        return {}
