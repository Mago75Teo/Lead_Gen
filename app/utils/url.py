from __future__ import annotations
import tldextract

def normalize_url(url: str) -> str:
    url = url.strip()
    if not url.startswith(("http://","https://")):
        url = "https://" + url
    return url

def domain_from_url(url: str) -> str:
    ext = tldextract.extract(url)
    if not ext.domain:
        return url
    return ".".join([p for p in [ext.domain, ext.suffix] if p])

def is_same_domain(url: str, domain: str) -> bool:
    return domain_from_url(url).lower() == domain.lower()
