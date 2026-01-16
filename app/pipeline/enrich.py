from __future__ import annotations
from typing import List, Dict, Any
import re

from ..models import CompanyCandidate, CompanyProfile, Evidence
from ..utils.scrape import fetch
from ..utils.tech_detect import detect_technologies
from ..utils.url import normalize_url, domain_from_url
from ..providers.opencorporates import OpenCorporatesClient
from ..settings import settings

ABOUT_PATHS = ["/chi-siamo", "/azienda", "/about", "/company", "/contatti", "/contact", "/lavora-con-noi", "/careers", "/news"]

def _guess_company_name(domain: str) -> str:
    return domain.split(".")[0].replace("-", " ").title()

def _extract_services_and_target(text: str) -> tuple[list[str], list[str]]:
    # Minimal heuristic extraction: bullet-like lines or keyword sections
    services = []
    targets = []
    for line in text.splitlines():
        s = line.strip(" -•	")
        if 3 <= len(s) <= 120:
            if re.search(r"(servizi|soluzioni|prodotti|impianti|software|sistemi)", s, re.IGNORECASE):
                services.append(s)
            if re.search(r"(clienti|settori|industria|retail|logistica|produzione|B2B|PMI|enterprise)", s, re.IGNORECASE):
                targets.append(s)
        if len(services) > 12 and len(targets) > 12:
            break
    return list(dict.fromkeys(services))[:12], list(dict.fromkeys(targets))[:12]

async def enrich_company(candidate: CompanyCandidate) -> CompanyProfile:
    base = normalize_url(candidate.website)
    domain = domain_from_url(base)
    html = ""
    evidences = list(candidate.evidences)

    # Fetch homepage
    try:
        html = await fetch(base)
    except Exception:
        # retry http if https fails
        if base.startswith("https://"):
            try:
                html = await fetch("http://" + domain)
                base = "http://" + domain
            except Exception:
                html = ""

    description = None
    services = []
    targets = []
    tech = detect_technologies(html) if html else []

    if html:
        from bs4 import BeautifulSoup
        # Use stdlib parser to avoid heavy lxml dependency (Vercel-friendly)
        soup = BeautifulSoup(html, "html.parser")
        title = (soup.title.string.strip() if soup.title and soup.title.string else None)
        if title:
            evidences.append(Evidence(title=title, url=base, snippet=None, source="site"))
        # meta description
        md = soup.find("meta", attrs={"name": "description"})
        if md and md.get("content"):
            description = md["content"].strip()

        # extract from visible text
        from ..utils.scrape import clean_text
        text = clean_text(html)
        services, targets = _extract_services_and_target(text)

    # Try a few common pages for more context
    for path in ABOUT_PATHS[:4]:
        try:
            phtml = await fetch(base.rstrip("/") + path)
            if phtml:
                from ..utils.scrape import clean_text
                t = clean_text(phtml)
                s2, t2 = _extract_services_and_target(t)
                services.extend(s2)
                targets.extend(t2)
                tech.extend(detect_technologies(phtml))
                evidences.append(Evidence(title=f"page:{path}", url=base.rstrip('/')+path, snippet=t[:250], source="site"))
        except Exception:
            continue

    services = list(dict.fromkeys([s for s in services if s and len(s) <= 140]))[:15]
    targets = list(dict.fromkeys([t for t in targets if t and len(t) <= 140]))[:15]
    tech = list(dict.fromkeys(tech))[:12]

    # Optional: OpenCorporates enrichment by name guess
    employees_est = None
    revenue_est = None
    headquarters = None
    if settings.OPENCORPORATES_API_KEY:
        try:
            oc = OpenCorporatesClient(settings.OPENCORPORATES_API_KEY)
            data = await oc.search_companies(query=_guess_company_name(domain))
            companies = (data.get("results") or {}).get("companies") or []
            if companies:
        # pull a couple fields if present
                c = (companies[0] or {}).get("company") or {}
                headquarters = c.get("registered_address_in_full") or c.get("registered_address")
                # employees/revenue often not present
        except Exception:
            pass

    return CompanyProfile(
        company_name=_guess_company_name(domain),
        website=base,
        province=candidate.province,
        industry=candidate.industry,
        description=description,
        services_products=services,
        target_customers=targets,
        technologies=tech,
        employees_est=employees_est,
        revenue_est_eur=revenue_est,
        headquarters=headquarters,
        recent_projects=candidate.growth_signals[:8],
        partners=[],
        evidences=evidences,
    )

async def enrich_candidates(candidates: List[CompanyCandidate]) -> List[CompanyProfile]:
    out: List[CompanyProfile] = []
    for c in candidates:
        out.append(await enrich_company(c))
    return out
