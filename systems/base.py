from abc import ABC, abstractmethod


class RpgSystem(ABC):
    name: str = ""

    @abstractmethod
    def run(self) -> None:
        """Start the interactive loop for this system."""
