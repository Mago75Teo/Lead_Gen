from __future__ import annotations
from typing import Optional
from ..settings import settings
from ..providers.search_base import SearchProvider
from ..providers.serper import SerperProvider
from ..providers.newsapi import NewsAPIProvider
from ..providers.perplexity_search import PerplexitySearchProvider
from ..providers.email_verify import HunterClient, GenericVerifier
from ..models import ApiKeys

def _pick(keys: Optional[ApiKeys], attr: str, fallback: Optional[str]) -> Optional[str]:
    return getattr(keys, attr) if keys and getattr(keys, attr, None) else fallback

def _pref(keys: Optional[ApiKeys]) -> str:
    return (_pick(keys, "web_provider", None) or "auto").strip().lower()

def get_search_provider(keys: Optional[ApiKeys] = None) -> SearchProvider:
    pref = _pref(keys)
    serper = _pick(keys, "serper_api_key", settings.SERPER_API_KEY)
    newsapi = _pick(keys, "newsapi_key", settings.NEWSAPI_KEY)
    pplx = _pick(keys, "perplexity_api_key", settings.PERPLEXITY_API_KEY)

    if pref == "perplexity" and pplx:
        return PerplexitySearchProvider(pplx)
    if pref == "serper" and serper:
        return SerperProvider(serper)
    if pref == "newsapi" and newsapi:
        return NewsAPIProvider(newsapi)

    # auto order
    if serper:
        return SerperProvider(serper)
    if pplx:
        return PerplexitySearchProvider(pplx)
    if newsapi:
        return NewsAPIProvider(newsapi)

    raise RuntimeError("No search provider configured. Provide SERPER_API_KEY or PERPLEXITY_API_KEY (or pass api_keys.* in request).")

def get_news_provider(keys: Optional[ApiKeys] = None) -> SearchProvider:
    return get_search_provider(keys)

def get_hunter_client(keys: Optional[ApiKeys] = None) -> Optional[HunterClient]:
    hunter = _pick(keys, "hunter_api_key", settings.HUNTER_API_KEY)
    return HunterClient(hunter) if hunter else None

def get_generic_verifier(keys: Optional[ApiKeys] = None):
    provider = _pick(keys, "email_verify_provider", settings.EMAIL_VERIFY_PROVIDER)
    api_key = _pick(keys, "email_verify_api_key", settings.EMAIL_VERIFY_API_KEY)
    return GenericVerifier(provider, api_key) if (provider and api_key) else None
