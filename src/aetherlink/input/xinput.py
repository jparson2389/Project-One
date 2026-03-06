"""Interface definitions for XInput controller state abstraction."""

from abc import ABC, abstractmethod


class XInputInterface(ABC):
    """Abstract base class for input interfaces."""

    @abstractmethod
    def read_controller_state(self) -> dict:
        """Read the current state of the controller.

        Returns:
            dict: The state of the controller.

        """
        pass

    @abstractmethod
    def write_controller_state(self, state: dict) -> None:
        """Write the state of the controller.

        Args:
            state (dict): The state to write to the controller.

        """
        pass
