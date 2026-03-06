from __future__ import annotations

from src.aetherlink.core.remote_play import RemotePlayPlugin


def test_remote_play_plugin_initialization() -> None:
    services = {}
    remote_play = RemotePlayPlugin(services)
    remote_play.initialize()
    assert remote_play is not None


def test_remote_play_plugin_start_stop() -> None:
    services = {}
    remote_play = RemotePlayPlugin(services)
    profile = {}
    remote_play.start(profile)
    remote_play.stop()
    assert remote_play is not None


def test_remote_play_plugin_get_capabilities() -> None:
    services = {}
    remote_play = RemotePlayPlugin(services)
    capabilities = remote_play.get_capabilities()
    expected_capabilities = {
        "plugin_id": "remote_play",
        "name": "Remote Play Plugin",
        "version": "1.0",
        "api_version": "1.0",
        "plugin_type": "Remote-play integrations",
    }
    assert capabilities == expected_capabilities
