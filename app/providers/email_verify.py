from __future__ import annotations
import httpx
from typing import Dict, Any, Optional, List

class EmailVerifier:
    async def verify(self, email: str) -> Dict[str, Any]:
        return {"status": "unknown"}

class HunterClient:
    """Hunter.io: domain search (trova email pubbliche) + verification."""
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def domain_search(self, domain: str, limit: int = 5) -> List[Dict[str, Any]]:
        url = "https://api.hunter.io/v2/domain-search"
        params = {"domain": domain, "api_key": self.api_key, "limit": limit}
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            data = r.json()
        return (data.get("data") or {}).get("emails", []) or []

    async def verify(self, email: str) -> Dict[str, Any]:
        url = "https://api.hunter.io/v2/email-verifier"
        params = {"email": email, "api_key": self.api_key}
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            return r.json()

class GenericVerifier(EmailVerifier):
    """Adapter generico: implementa qui integrazioni (ZeroBounce/NeverBounce/etc.)."""
    def __init__(self, provider: str, api_key: str):
        self.provider = provider.lower()
        self.api_key = api_key

    async def verify(self, email: str) -> Dict[str, Any]:
        # Placeholder: implementa in base al provider scelto
        return {"status": "unknown", "provider": self.provider, "note": "Implementa adapter in app/providers/email_verify.py"}
