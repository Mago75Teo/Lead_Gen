from __future__ import annotations

"""Perplexity web search provider.

⚠️  Vercel imports all Python modules reachable at build time. If this module
fails to import, the whole Function crashes with 500.

The rest of the pipeline expects search results as a list of dictionaries with
keys like: title, link/url, snippet, date.
"""

from typing import List, Dict, Any, Optional
import httpx

from .search_base import SearchProvider

COUNTRY_MAP = {
    "italia": "IT",
    "italy": "IT",
    "united states": "US",
    "usa": "US",
    "germany": "DE",
    "deutschland": "DE",
    "france": "FR",
    "spain": "ES",
    "uk": "GB",
    "united kingdom": "GB",
}

class PerplexitySearchProvider(SearchProvider):
    """Perplexity Search API: POST https://api.perplexity.ai/search

    Perplexity's API does not have separate "web" vs "news" endpoints.
    We expose both methods and map them to the same underlying search.
    """

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def _search(
        self,
        query: str,
        max_results: int = 10,
        country: Optional[str] = None,
        recency: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        url = "https://api.perplexity.ai/search"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload: Dict[str, Any] = {
            "query": query,
            "max_results": max(1, min(int(max_results), 20)),
            "max_tokens_per_page": 1024,
            "max_tokens": 12000,
        }
        if country:
            cc = COUNTRY_MAP.get(country.strip().lower())
            if cc:
                payload["country"] = cc
        if recency:
            payload["search_recency_filter"] = recency  # day|week|month|year

        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(url, headers=headers, json=payload)
            r.raise_for_status()
            data = r.json()

        results: List[Dict[str, Any]] = []
        for item in (data.get("results") or [])[: payload["max_results"]]:
            # Normalize to the shape expected by pipeline/discover.py
            results.append(
                {
                    "title": item.get("title") or "",
                    "link": item.get("url") or "",
                    "url": item.get("url") or "",
                    "snippet": item.get("snippet") or "",
                    "date": item.get("date") or None,
                    "source": "perplexity",
                    "raw": item,
                }
            )
        return results

    async def web_search(self, query: str, num: int = 10, **kwargs) -> List[Dict[str, Any]]:
        return await self._search(
            query=query,
            max_results=num,
            country=kwargs.get("country"),
            recency=kwargs.get("recency"),
        )

    async def news_search(self, query: str, num: int = 10, **kwargs) -> List[Dict[str, Any]]:
        # Perplexity doesn't expose a dedicated news endpoint; reuse web search.
        return await self.web_search(query=query, num=num, **kwargs)
