from __future__ import annotations
import httpx
from typing import List, Dict, Any, Optional
from .search_base import SearchProvider

class SerperProvider(SearchProvider):
    """Serper.dev provider (Google Search + Google News)"""
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def _post(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        headers = {"X-API-KEY": self.api_key, "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(endpoint, headers=headers, json=payload)
            r.raise_for_status()
            return r.json()

    async def web_search(self, query: str, num: int = 10, **kwargs) -> List[Dict[str, Any]]:
        data = await self._post("https://google.serper.dev/search", {"q": query, "num": num})
        return data.get("organic", []) or []

    async def news_search(self, query: str, num: int = 10, **kwargs) -> List[Dict[str, Any]]:
        data = await self._post("https://google.serper.dev/news", {"q": query, "num": num})
        return data.get("news", []) or []
