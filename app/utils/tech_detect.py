from __future__ import annotations
import re
from typing import List

SIGNATURES = [
    ("WordPress", [r"wp-content", r"wp-includes"]),
    ("WooCommerce", [r"woocommerce", r"wc-"]),
    ("Shopify", [r"cdn\.shopify\.com", r"Shopify"]),
    ("Google Tag Manager", [r"googletagmanager\.com/gtm\.js"]),
    ("Google Analytics", [r"google-analytics\.com", r"gtag\("]),
    ("HubSpot", [r"js\.hs-scripts\.com", r"hubspot"]),
]

def detect_technologies(html: str, max_items: int = 10) -> List[str]:
    hits: List[str] = []
    for name, patterns in SIGNATURES:
        for p in patterns:
            if re.search(p, html, re.IGNORECASE):
                hits.append(name)
                break
        if len(hits) >= max_items:
            break
    return list(dict.fromkeys(hits))
