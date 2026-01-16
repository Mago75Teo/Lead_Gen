from __future__ import annotations
import httpx
from typing import Any, Dict, List

class OpenAIProvider:
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def chat(self, messages: List[Dict[str, str]], model: str, temperature: float = 0.2) -> Dict[str, Any]:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {"model": model, "messages": messages, "temperature": temperature}
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(url, headers=headers, json=payload)
            r.raise_for_status()
            data = r.json()
        content = data["choices"][0]["message"]["content"]
        return {"content": content, "raw": data, "usage": data.get("usage")}
