from __future__ import annotations
from typing import List, Dict, Any, Set
from ..models import CompanyCandidate, Evidence, Geography, Segment
from ..utils.url import normalize_url, domain_from_url
from .providers_factory import get_search_provider, get_news_provider
from ..config_loader import FocusConfig

def _build_queries(industry: str, geo: Geography, growth_keywords: List[str]) -> List[str]:
    provinces = geo.provinces or []
    # Query set: combine industry + province + growth signal keywords
    q = []
    for prov in provinces:
        for kw in growth_keywords[:6]:
            q.append(f'{industry} {prov} {kw} azienda')
        # general
        q.append(f'{industry} aziende {prov}')
        q.append(f'{industry} {prov} investe ampliamento')
    return q

def _result_to_evidence(item: Dict[str, Any], source: str) -> Evidence:
    return Evidence(
        title=item.get("title") or item.get("name") or "result",
        url=item.get("link") or item.get("url") or "",
        snippet=item.get("snippet") or item.get("description"),
        published_at=item.get("date") or item.get("publishedAt"),
        source=source,
    )

async def discover_candidates(
    focus: FocusConfig,
    industry: str,
    geo: Geography,
    segment: Segment,
    limit: int = 30,
    api_keys=None,
    preset=None,
) -> List[CompanyCandidate]:
    search = get_search_provider(api_keys)
    news = get_news_provider(api_keys)

    queries = _build_queries(industry=industry, geo=geo, growth_keywords=focus.growth_keywords)
    seen_domains: Set[str] = set()
    candidates: List[CompanyCandidate] = []

    for q in queries:
        if len(candidates) >= limit:
            break

        # Web results
        web_results = await search.web_search(q, num=10)
        for item in web_results:
            url = item.get("link") or ""
            if not url:
                continue
            dom = domain_from_url(url)
            if not dom or dom in seen_domains:
                continue
            seen_domains.add(dom)
            candidates.append(CompanyCandidate(
                company_name=dom,
                website=normalize_url(dom),
                province=None,
                industry=industry,
                growth_signals=[],
                evidences=[_result_to_evidence(item, source="web")],
            ))
            if len(candidates) >= limit:
                break

        if len(candidates) >= limit:
            break

        # News results (growth signals)
        news_results = await news.news_search(q, num=5)
        for item in news_results:
            url = item.get("link") or item.get("url") or ""
            if not url:
                continue
            dom = domain_from_url(url)
            if not dom:
                continue
            # attach evidence to existing or create new
            ev = _result_to_evidence(item, source="news")
            existing = next((c for c in candidates if domain_from_url(c.website) == dom), None)
            if existing:
                existing.evidences.append(ev)
                if item.get("title"):
                    existing.growth_signals.append(item.get("title"))
            else:
                if dom in seen_domains:
                    continue
                seen_domains.add(dom)
                candidates.append(CompanyCandidate(
                    company_name=dom,
                    website=normalize_url(dom),
                    province=None,
                    industry=industry,
                    growth_signals=[item.get("title") or "news"],
                    evidences=[ev],
                ))
            if len(candidates) >= limit:
                break

    return candidates[:limit]
