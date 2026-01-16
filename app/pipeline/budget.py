from __future__ import annotations
from typing import Optional, Tuple
import re
from ..models import CompanyProfile

# Robust-ish heuristic to estimate whether a prospect likely has budget 30k–50k+
# for projects in security/ICT/plant operations domains.
#
# Returns (estimated_budget_eur, rationale)

INDUSTRY_MULTIPLIER = {
    "logistica": 1.15,
    "produzione": 1.15,
    "automotive": 1.25,
    "retail": 1.05,
    "hospitality": 0.95,
    "sanità": 1.10,
    "energia": 1.25,
}

KEYWORD_BOOSTS = [
    (r"(ampliamento|nuov(a|e)\s+sede|nuov(o|a)\s+stabilimento|nuov(o|a)\s+magazzino)", 0.20),
    (r"(investimento|capex|piano\s+industriale|modernizzazione|revamping)", 0.15),
    (r"(bando|gara|aggiudicazione|commessa|appalto)", 0.12),
    (r"(sicurezza|videosorveglianza|controllo\s+accessi|antintrusione|cctv)", 0.10),
    (r"(ict|it\s+infrastructure|cyber|soc|siem|iso\s*27001)", 0.10),
    (r"(automation|automazione|robot|wms|mes|erp)", 0.10),
    (r"(data\s+center|cloud\s+migration|sd-wan)", 0.08),
]

def _clamp(x: float, a: float, b: float) -> float:
    return max(a, min(b, x))

def estimate_budget(company: CompanyProfile, project_profile=None, preset=None) -> Tuple[Optional[int], str]:
    score = 0.35
    rationale = []

    if company.employees_est:
        emp = company.employees_est
        if emp >= 1000:
            score += 0.30; rationale.append("dipendenti>=1000")
        elif emp >= 250:
            score += 0.22; rationale.append("dipendenti>=250")
        elif emp >= 50:
            score += 0.14; rationale.append("dipendenti>=50")
        else:
            score += 0.05; rationale.append("dipendenti<50")

    if company.revenue_est_eur:
        rev = company.revenue_est_eur
        if rev >= 100_000_000:
            score += 0.25; rationale.append("fatturato>=100M")
        elif rev >= 20_000_000:
            score += 0.16; rationale.append("fatturato>=20M")
        elif rev >= 5_000_000:
            score += 0.08; rationale.append("fatturato>=5M")

    evid = len(company.evidences or [])
    if evid >= 8:
        score += 0.14; rationale.append("evidenze>=8")
    elif evid >= 4:
        score += 0.08; rationale.append("evidenze>=4")

    corpus = " ".join([
        company.description or "",
        " ".join(company.services_products or []),
        " ".join(company.recent_projects or []),
        " ".join(company.target_customers or []),
        " ".join(company.technologies or []),
    ]).lower()

    kw = 0.0
    for pat, b in KEYWORD_BOOSTS:
        if re.search(pat, corpus, re.IGNORECASE):
            kw += b

    # Preset-specific boosts
    if preset and getattr(preset, 'budget_keyword_boosts', None):
        for item in preset.budget_keyword_boosts:
            try:
                pat = item.get('pattern')
                b = float(item.get('boost', 0))
                if pat and re.search(pat, corpus, re.IGNORECASE):
                    kw += b
            except Exception:
                continue
    if kw:
        boost = _clamp(kw, 0.0, 0.35)
        score += boost
        rationale.append(f"keyword_boost={boost:.2f}")

    ind = (company.industry or "").strip().lower()
    mult = INDUSTRY_MULTIPLIER.get(ind, 1.0)
    score *= mult
    if mult != 1.0:
        rationale.append(f"sector_mult={mult:.2f}")

    score = _clamp(score, 0.0, 1.0)

    # Calibrazione con Project Profile (se disponibile)
    if project_profile:
        tmin = getattr(project_profile, 'typical_deal_min_eur', None)
        tmax = getattr(project_profile, 'typical_deal_max_eur', None)
        if isinstance(tmin, int) and tmin >= 50000:
            score = _clamp(score + 0.05, 0.0, 1.0)
        if isinstance(tmax, int) and tmax >= 100000:
            score = _clamp(score + 0.05, 0.0, 1.0)

    if score < 0.45:
        est = 20000; band = "<30k"
    elif score < 0.60:
        est = 40000; band = "30–50k"
    elif score < 0.78:
        est = 75000; band = "50–100k"
    else:
        est = 125000; band = "100k+"

    rat = " | ".join(rationale) if rationale else "segnali minimi"
    return est, f"band={band}; score={score:.2f}; {rat}"
