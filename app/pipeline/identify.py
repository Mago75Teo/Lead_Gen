from __future__ import annotations
from typing import List, Optional
import re

from ..models import CompanyProfile, DecisionMaker
from ..utils.scrape import fetch, clean_text

DM_ROLE_PATTERNS = [
    ("CEO", r"(CEO|Chief Executive Officer|Amministratore Delegato|AD)"),
    ("General Manager", r"(General Manager|Direttore Generale)"),
    ("Direttore Operations", r"(Direttore Operations|Operations Director|Direttore Produzione|Plant Manager|Responsabile Produzione)"),
    ("Responsabile ICT", r"(CIO|IT Manager|Responsabile IT|Responsabile ICT|Direttore ICT)"),
    ("Responsabile Acquisti", r"(Procurement|Responsabile Acquisti|Buyer|Purchasing)"),
    ("Direttore Commerciale", r"(Sales Director|Direttore Commerciale)"),
    ("Direttore Marketing", r"(Marketing Director|Direttore Marketing)"),
]

PEOPLE_PAGES = ["/team","/chi-siamo","/azienda","/about","/contatti","/contact","/organigramma"]

def _extract_people(text: str) -> List[DecisionMaker]:
    # Heuristic: find "Name Surname – Role" like patterns in lines
    dms: List[DecisionMaker] = []
    for line in text.splitlines():
        s = line.strip()
        if len(s) < 8 or len(s) > 140:
            continue
        # look for roles
        for role, pat in DM_ROLE_PATTERNS:
            if re.search(pat, s, re.IGNORECASE):
                # try to capture a name before role
                m = re.search(r"([A-ZÀ-ÖØ-Ý][\w'’\-]+\s+[A-ZÀ-ÖØ-Ý][\w'’\-]+)", s)
                name = m.group(1) if m else "N/D"
                dms.append(DecisionMaker(name=name, role=role, source_url=None, linkedin_url=None))
                break
        if len(dms) >= 6:
            break
    # de-dup by (name,role)
    seen = set()
    uniq = []
    for d in dms:
        key = (d.name.lower(), d.role.lower())
        if key not in seen:
            seen.add(key)
            uniq.append(d)
    return uniq

async def identify_decision_maker(company: CompanyProfile) -> Optional[DecisionMaker]:
    base = company.website.rstrip("/")
    best: Optional[DecisionMaker] = None

    # Try people pages
    for path in PEOPLE_PAGES:
        try:
            html = await fetch(base + path)
            txt = clean_text(html)
            people = _extract_people(txt)
            if people:
                # priority order based on DM_ROLE_PATTERNS
                best = people[0]
                best.source_url = base + path
                return best
        except Exception:
            continue

    # fallback: none found
    return None

async def identify_for_companies(companies: List[CompanyProfile]) -> List[tuple[CompanyProfile, Optional[DecisionMaker]]]:
    out = []
    for c in companies:
        out.append((c, await identify_decision_maker(c)))
    return out
