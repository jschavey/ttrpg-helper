from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional


class RpgSystem(ABC):
    name: str = ""
    system_slug: str = ""

    @abstractmethod
    def run(self, character: Optional[object] = None) -> None:
        """Start the interactive loop for this system."""
