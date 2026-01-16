from __future__ import annotations
import dns.resolver
from typing import Tuple

def has_mx(domain: str) -> Tuple[bool, str]:
    try:
        answers = dns.resolver.resolve(domain, "MX")
        mx = ",".join([str(r.exchange).rstrip(".") for r in answers])
        return True, mx
    except Exception as e:
        return False, str(e)
