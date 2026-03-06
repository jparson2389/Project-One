"""Data models defining the standard native Application Binary Interface."""

from typing import Any

from pydantic import BaseModel


class PluginIdentity(BaseModel):
    """Represents the identity of a plugin."""

    plugin_id: str
    name: str


class Lifecycle(BaseModel):
    """Defines lifecycle methods for a plugin."""

    Initialize: Any
    Start: Any
    Shutdown: Any


class Capabilities(BaseModel):
    """Describes the capabilities of a plugin."""

    GetCapabilities: Any


class PluginPolicy(BaseModel):
    """Defines policy requirements for a plugin."""

    required_entitlements: list[str]
    requires_drivers: list[str]
    requires_worker: bool


class PluginContract(BaseModel):
    """Represents the contract of a plugin."""

    identity: PluginIdentity
    lifecycle: Lifecycle
