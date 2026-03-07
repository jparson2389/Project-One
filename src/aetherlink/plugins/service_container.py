"""Service container module for Aetherlink host services."""
from __future__ import annotations

from typing import Any

from loguru import logger


class ServiceContainer:
    """Typed registry for host services.

    Provides register/get access for named services such as
    logging, config, auth, and telemetry.
    """

    def __init__(self) -> None:
        """Initialize an empty service registry."""
        self._services: dict[str, Any] = {}

    def register(self, name: str, instance: Any) -> None:
        """Register a named service instance.

        Args:
            name: Unique service identifier.
            instance: The service object to register.

        """
        logger.debug(f'Registering service: {name}')
        self._services[name] = instance

    def get(self, name: str) -> Any:
        """Retrieve a registered service by name.

        Args:
            name: The service identifier.

        Returns:
            The registered service instance.

        Raises:
            KeyError: If no service is registered under that name.

        """
        if name not in self._services:
            raise KeyError(f'Service not found: {name!r}')
        return self._services[name]
