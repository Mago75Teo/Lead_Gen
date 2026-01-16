from __future__ import annotations
from typing import List, Optional
import re

from ..models import LeadRecord, VerifiedEmail
from ..utils.url import domain_from_url
from ..utils.email_dns import has_mx
from .providers_factory import get_hunter_client, get_generic_verifier

COMMON_PATTERNS = [
    "{first}.{last}@{domain}",
    "{first}{last}@{domain}",
    "{f}{last}@{domain}",
    "{first}_{last}@{domain}",
]

def _split_name(full_name: str) -> tuple[Optional[str], Optional[str]]:
    if not full_name or full_name == "N/D":
        return None, None
    parts = re.split(r"\s+", full_name.strip())
    if len(parts) < 2:
        return None, None
    first = re.sub(r"[^a-zA-ZÀ-ÖØ-öø-ÿ]", "", parts[0]).lower()
    last = re.sub(r"[^a-zA-ZÀ-ÖØ-öø-ÿ]", "", parts[-1]).lower()
    return first, last

async def verify_leads(leads: List[LeadRecord], api_keys=None) -> List[LeadRecord]:
    hunter = get_hunter_client(api_keys)
    verifier = get_generic_verifier(api_keys)

    for lead in leads:
        dom = domain_from_url(lead.company.website)
        if not dom:
            continue

        # 1) Basic MX check
        mx_ok, mx_info = has_mx(dom)
        if not mx_ok:
            lead.verified_email = VerifiedEmail(email="", status="invalid", source="mx", details={"mx": mx_info})
            continue

        # 2) If Hunter is available, try domain search for relevant emails
        if hunter:
            try:
                emails = await hunter.domain_search(dom, limit=10)
                # pick best match for role/name if possible
                if emails:
                    # Prefer seniority if present; else first
                    chosen = emails[0]
                    email = chosen.get("value") or ""
                    # verify via hunter
                    v = await hunter.verify(email)
                    status = ((v.get("data") or {}).get("status")) or "unknown"
                    # Map to our statuses
                    mapped = "valid" if status in ("valid","accept_all") else ("invalid" if status in ("invalid","reject") else "unknown")
                    lead.verified_email = VerifiedEmail(email=email, status=mapped, source="hunter", details={"hunter": v})
                    lead.contact_source = "hunter"
                    continue
            except Exception:
                pass

        # 3) Pattern generation + optional verifier
        if lead.decision_maker and lead.decision_maker.name and lead.decision_maker.name != "N/D":
            first, last = _split_name(lead.decision_maker.name)
            if first and last:
                guesses = [p.format(first=first, last=last, f=first[:1], domain=dom) for p in COMMON_PATTERNS]
                # de-dup
                guesses = list(dict.fromkeys(guesses))[:5]
                # verify guesses if verifier available
                if verifier:
                    for g in guesses:
                        res = await verifier.verify(g)
                        status = res.get("status","unknown")
                        mapped = "valid" if status in ("valid","deliverable") else ("invalid" if status in ("invalid","undeliverable") else "unknown")
                        if mapped == "valid":
                            lead.verified_email = VerifiedEmail(email=g, status="valid", source="verifier", details=res)
                            lead.contact_source = "pattern+verifier"
                            break
                if not lead.verified_email:
                    lead.verified_email = VerifiedEmail(email=guesses[0], status="unknown", source="pattern", details={"mx": mx_info, "guesses": guesses})
                    lead.contact_source = "pattern"

    return leads
