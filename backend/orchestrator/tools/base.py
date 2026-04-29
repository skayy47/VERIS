from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Tool(ABC):
    name: str
    description: str

    @abstractmethod
    async def run(self, **kwargs: Any) -> Any:
        """Execute the tool with the given parameters."""
        ...
