import re
import httpx
from bs4 import BeautifulSoup
from typing import List, Tuple

DEFAULT_HEADERS = {"User-Agent": "lead-scouting-agent/1.0"}

def clean_text(html: str) -> str:
    # Use stdlib parser to avoid heavy lxml dependency (Vercel-friendly)
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script","style","noscript","iframe"]):
        tag.decompose()
    text = soup.get_text("\n")
    text = re.sub(r"\n{2,}", "\n\n", text)
    return text.strip()

async def fetch(url: str) -> str:
    async with httpx.AsyncClient(timeout=60, follow_redirects=True, headers=DEFAULT_HEADERS) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.text

async def fetch_many(urls: List[str], limit: int = 5) -> List[Tuple[str, str]]:
    out = []
    for u in urls[:limit]:
        try:
            out.append((u, await fetch(u)))
        except Exception:
            continue
    return out
