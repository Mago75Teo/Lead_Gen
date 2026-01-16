from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class SearchProvider(ABC):
    @abstractmethod
    async def web_search(self, query: str, num: int = 10, **kwargs) -> List[Dict[str, Any]]:
        ...

    @abstractmethod
    async def news_search(self, query: str, num: int = 10, **kwargs) -> List[Dict[str, Any]]:
        ...
