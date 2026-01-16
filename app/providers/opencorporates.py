from __future__ import annotations
import httpx
from typing import Dict, Any, Optional

class OpenCorporatesClient:
    """Enrichment opzionale: cerca azienda per nome e restituisce dati base (se disponibili)."""
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key

    async def search_companies(self, query: str, country_code: str = "it", per_page: int = 5) -> Dict[str, Any]:
        url = "https://api.opencorporates.com/v0.4/companies/search"
        params = {"q": query, "jurisdiction_code": f"{country_code}", "per_page": per_page}
        if self.api_key:
            params["api_token"] = self.api_key
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            return r.json()
