from __future__ import annotations
from typing import List, Dict, Any, Optional
from ..models import LeadRecord
from ..settings import settings
from ..llm.openai_provider import OpenAIProvider

SYSTEM = """Sei un assistente commerciale B2B. Scrivi email brevi, professionali e personalizzate.
Non inventare dati: se manca un dettaglio, usa formule neutre (es. "ho notato che...") e cita SOLO ciò che è in input.
Obiettivo: richiedere un meeting di 15-20 minuti."""

def _lead_context(lead: LeadRecord) -> str:
    c = lead.company
    dm = lead.decision_maker
    evidence = (c.evidences[0].title if c.evidences else None)
    return f"""Prospect:
- Azienda: {c.company_name}
- Sito: {c.website}
- Settore: {c.industry}
- Trigger: {', '.join(c.recent_projects or [])}
- Evidenza: {evidence}

Decision maker:
- Nome: {(dm.name if dm else 'N/D')}
- Ruolo: {(dm.role if dm else 'N/D')}

Obiettivo: proporre incontro per valutare esigenze su sicurezza/impianti/ICT (personalizza in base al caso).
"""

async def generate_email_drafts(leads: List[LeadRecord], sender_company: str = "Teleimpianti S.p.A.", api_keys=None, project_profile=None, preset=None) -> List[Dict[str, Any]]:
    if preset and getattr(preset, 'sender_company', None):
        sender_company = preset.sender_company

    api_key = getattr(api_keys, "openai_api_key", None) if api_keys else None
    model = getattr(api_keys, "openai_model", None) if api_keys else None
    api_key = api_key or settings.OPENAI_API_KEY
    model = model or settings.OPENAI_MODEL
    if settings.LLM_PROVIDER != "openai" or not api_key:
        return []

    llm = OpenAIProvider(api_key)
    out = []
    for lead in leads:
        ctx = _lead_context(lead)
        user = f"Scrivi una bozza email per fissare un appuntamento. Mittente: {sender_company}.\n\n{ctx}"
        res = await llm.chat(
            model=model,
            messages=[{"role":"system","content":SYSTEM},{"role":"user","content":user}],
            temperature=0.2,
        )
        out.append({
            "company": lead.company.company_name,
            "email_to": (lead.verified_email.email if lead.verified_email else ""),
            "draft": res["content"],
        })
    return out
