from __future__ import annotations
from typing import List, Optional, Tuple
import re
import json
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

from ..models import ProjectProfile, ApiKeys
from ..profile_cache import get_profile, set_profile, purge_expired, delete_profile
from ..settings import settings

KEY_PAGES_HINTS = [
    "servizi","service","solutions","soluzioni","impianti","videosorveglianza","sicurezza",
    "ict","it","cyber","case-study","case studies","referenze","clienti","partner",
    "chi-siamo","about","contatti","contact"
]

def _same_domain(a: str, b: str) -> bool:
    try:
        return urlparse(a).netloc == urlparse(b).netloc
    except Exception:
        return False

def _clean_text(html: str) -> str:
    # Use stdlib parser to avoid heavy lxml dependency (Vercel-friendly)
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script","style","noscript"]):
        tag.decompose()
    text = soup.get_text("\n")
    text = re.sub(r"\n{2,}", "\n\n", text)
    return text.strip()

async def _fetch(url: str) -> str:
    async with httpx.AsyncClient(timeout=45, follow_redirects=True) as client:
        r = await client.get(url, headers={"User-Agent": "lead-scouting-agent/1.0"})
        r.raise_for_status()
        return r.text

def _pick_links(base_url: str, html: str, limit: int = 8) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        u = urljoin(base_url, href)
        if not _same_domain(u, base_url):
            continue
        txt = (a.get_text(" ") or "").strip().lower()
        href_l = href.lower()
        if any(k in txt or k in href_l for k in KEY_PAGES_HINTS):
            links.append(u)
    out, seen = [], set()
    for u in links:
        if u not in seen:
            seen.add(u); out.append(u)
        if len(out) >= limit:
            break
    return out

def _extract_lists(text: str) -> Tuple[List[str], List[str], List[str], List[str]]:
    lines = [l.strip(" -•\t") for l in text.splitlines() if l.strip()]
    candidates = [l for l in lines if 3 <= len(l) <= 90]
    services, tech, industries, proof = [], [], [], []
    for c in candidates:
        cl = c.lower()
        if any(k in cl for k in ["videosorveglianza","antintrusione","cctv","controllo accessi","impianti","sicurezza","manutenzione","assistenza","progettazione","installazione","cablaggio","rete","network","wi-fi","cyber","firewall","server","voip","tvcc"]):
            services.append(c)
        if any(k in cl for k in ["siem","soc","iso","onvif","rtsp","poe","vms","cloud","azure","aws","vmware","fortinet","cisco","mikrotik","sap","erp","wms","mes"]):
            tech.append(c)
        if any(k in cl for k in ["automotive","logistica","retail","industria","produzione","hospitality","sanità","energia","pubblica amministrazione","pa"]):
            industries.append(c)
        if any(k in cl for k in ["case","studio","cliente","referenza","partner","certificazione","progetto","installato","realizzato"]):
            proof.append(c)
    def dedup(xs, n):
        out=[]; seen=set()
        for x in xs:
            if x not in seen:
                seen.add(x); out.append(x)
        return out[:n]
    return dedup(services,12), dedup(industries,10), dedup(tech,12), dedup(proof,10)

async def _llm_profile(text: str, keys: Optional[ApiKeys]) -> Optional[ProjectProfile]:
    openai_key = (keys.openai_api_key if keys and getattr(keys,"openai_api_key",None) else None) or settings.OPENAI_API_KEY
    openai_model = (keys.openai_model if keys and getattr(keys,"openai_model",None) else None) or settings.OPENAI_MODEL
    pplx_key = (keys.perplexity_api_key if keys and getattr(keys,"perplexity_api_key",None) else None) or settings.PERPLEXITY_API_KEY

    schema = {
      "type": "object",
      "properties": {
        "services_offered": {"type":"array","items":{"type":"string"}},
        "industries_served": {"type":"array","items":{"type":"string"}},
        "technologies": {"type":"array","items":{"type":"string"}},
        "value_props": {"type":"array","items":{"type":"string"}},
        "proof_points": {"type":"array","items":{"type":"string"}},
        "typical_deal_min_eur": {"type":["integer","null"]},
        "typical_deal_max_eur": {"type":["integer","null"]},
        "notes": {"type":["string","null"]}
      },
      "required": ["services_offered","industries_served","technologies","value_props","proof_points","typical_deal_min_eur","typical_deal_max_eur","notes"]
    }

    prompt = (
        "Estrai un profilo offerta B2B dal testo del sito (italiano).\n"
        "Restituisci SOLO JSON conforme allo schema.\n"
        "- services_offered: max 12\n"
        "- industries_served: max 10\n"
        "- technologies: max 12\n"
        "- value_props: max 8\n"
        "- proof_points: max 10\n"
        "- typical_deal_min_eur/max_eur: se deducibile; altrimenti null\n"
    )

    content = text[:12000]

    # OpenAI (se presente)
    if openai_key:
        try:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {"Authorization": f"Bearer {openai_key}"}
            payload = {
                "model": openai_model,
                "temperature": 0.2,
                "response_format": {"type":"json_schema","json_schema":{"name":"project_profile","schema":schema}},
                "messages": [
                    {"role":"system","content":"Sei un analista B2B. Produci output JSON valido."},
                    {"role":"user","content": prompt + "\n\nTESTO:\n" + content}
                ]
            }
            async with httpx.AsyncClient(timeout=60) as client:
                r = await client.post(url, headers=headers, json=payload)
                r.raise_for_status()
                data = r.json()
            txt = data["choices"][0]["message"]["content"]
            obj = json.loads(txt)
            return ProjectProfile(reference_url="", **obj)
        except Exception:
            pass

    # Perplexity chat (OpenAI-compatible)
    if pplx_key:
        try:
            url = "https://api.perplexity.ai/chat/completions"
            headers = {"Authorization": f"Bearer {pplx_key}", "Content-Type":"application/json"}
            payload = {
                "model": "sonar-pro",
                "temperature": 0.2,
                "response_format": {"type":"json_schema","json_schema":{"name":"project_profile","schema":schema}},
                "messages": [
                    {"role":"system","content":"You are a B2B analyst. Output MUST be valid JSON only."},
                    {"role":"user","content": prompt + "\n\nTEXT:\n" + content}
                ]
            }
            async with httpx.AsyncClient(timeout=60) as client:
                r = await client.post(url, headers=headers, json=payload)
                r.raise_for_status()
                data = r.json()
            txt = data["choices"][0]["message"]["content"]
            obj = json.loads(txt)
            return ProjectProfile(reference_url="", **obj)
        except Exception:
            pass

    return None

async def build_project_profile(reference_url: str, keys: Optional[ApiKeys] = None, force_refresh: bool = False) -> ProjectProfile:
    # Cache TTL: ~6 mesi (183 giorni). Purge automatica ad ogni chiamata.
    purge_expired()
    if force_refresh:
        delete_profile(reference_url)
    cached = get_profile(reference_url)
    if (not force_refresh) and cached.hit and cached.value:
        try:
            return ProjectProfile(**cached.value)
        except Exception:
            pass
    home_html = await _fetch(reference_url)
    links = _pick_links(reference_url, home_html, limit=8)

    pages = [_clean_text(home_html)]
    for u in links:
        try:
            pages.append(_clean_text(await _fetch(u)))
        except Exception:
            continue

    combined = "\n\n---\n\n".join(pages)

    llm_prof = await _llm_profile(combined, keys)
    if llm_prof:
        llm_prof.reference_url = reference_url
        set_profile(reference_url, llm_prof.model_dump())
        return llm_prof

    services, industries, tech, proof = _extract_lists(combined)
    prof = ProjectProfile(
        reference_url=reference_url,
        services_offered=services,
        industries_served=industries,
        technologies=tech,
        value_props=[],
        proof_points=proof,
        typical_deal_min_eur=None,
        typical_deal_max_eur=None,
        notes="profilo estratto via euristiche (nessun LLM disponibile)",
    )

    set_profile(reference_url, prof.model_dump())
    return prof
