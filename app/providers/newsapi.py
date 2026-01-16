from __future__ import annotations
import httpx
from typing import List, Dict, Any
from .search_base import SearchProvider

class NewsAPIProvider(SearchProvider):
    """NewsAPI provider. Note: web_search non supportata; usa news_search."""
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def web_search(self, query: str, num: int = 10, **kwargs) -> List[Dict[str, Any]]:
        return []

    async def news_search(self, query: str, num: int = 10, **kwargs) -> List[Dict[str, Any]]:
        url = "https://newsapi.org/v2/everything"
        params = {"q": query, "pageSize": min(num, 100), "language": "it", "sortBy": "publishedAt"}
        headers = {"X-Api-Key": self.api_key}
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.get(url, params=params, headers=headers)
            r.raise_for_status()
            data = r.json()
        out = []
        for a in data.get("articles", [])[:num]:
            out.append({
                "title": a.get("title"),
                "link": a.get("url"),
                "snippet": a.get("description"),
                "date": a.get("publishedAt"),
                "source": (a.get("source") or {}).get("name", "newsapi"),
            })
        return out
