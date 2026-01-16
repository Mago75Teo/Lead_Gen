from __future__ import annotations

from typing import List, Optional, Dict, Any
import csv
import io
import re

from ..models import CompanyProfile, DecisionMaker, LeadRecord, VerifiedEmail, Evidence
from .budget import estimate_budget

# Vercel bundle-size friendly: avoid pandas/numpy.

COLUMN_ALIASES: Dict[str, List[str]] = {
    "first_name": ["first name", "nome", "firstname", "given name"],
    "last_name": ["last name", "cognome", "lastname", "family name"],
    "company": ["company", "azienda", "current company", "società", "societa"],
    "position": ["position", "ruolo", "title", "job title"],
    "email": ["email address", "email", "e-mail"],
    "linkedin_url": ["url", "profile url", "linkedin url", "public profile url"],
    "website": ["website", "company website", "sito", "site"],
}


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", str(s or "").strip().lower())


def _pick_col(cols: List[str], aliases: List[str]) -> Optional[str]:
    norm_cols = {_norm(c): c for c in cols}
    for a in aliases:
        na = _norm(a)
        if na in norm_cols:
            return norm_cols[na]

    for c in cols:
        cn = _norm(c)
        for a in aliases:
            if _norm(a) in cn:
                return c

    return None


def _mapped(mapping: Optional[Dict[str, Any]], key: str, cols: List[str]) -> Optional[str]:
    if not mapping:
        return None
    val = mapping.get(key)
    if not val:
        return None

    # exact match (case sensitive) or case-insensitive fallback
    if val in cols:
        return val
    for c in cols:
        if _norm(c) == _norm(val):
            return c

    return None


def _sniff_dialect(sample: str) -> csv.Dialect:
    try:
        return csv.Sniffer().sniff(sample, delimiters=[",", ";", "\t", "|"])
    except Exception:
        return csv.get_dialect("excel")


def parse_linkedin_csv(content: bytes, mapping: Optional[Dict[str, Any]] = None) -> List[LeadRecord]:
    # Handle UTF-8 BOM and strange encodings gracefully
    text = content.decode("utf-8-sig", errors="replace")
    sample = "\n".join(text.splitlines()[:5])
    dialect = _sniff_dialect(sample)

    f = io.StringIO(text)
    reader = csv.DictReader(f, dialect=dialect)
    cols = [c for c in (reader.fieldnames or []) if c is not None]

    c_first = _mapped(mapping, "first_name", cols) or _pick_col(cols, COLUMN_ALIASES["first_name"])
    c_last = _mapped(mapping, "last_name", cols) or _pick_col(cols, COLUMN_ALIASES["last_name"])
    c_company = _mapped(mapping, "company", cols) or _pick_col(cols, COLUMN_ALIASES["company"])
    c_pos = _mapped(mapping, "position", cols) or _pick_col(cols, COLUMN_ALIASES["position"])
    c_email = _mapped(mapping, "email", cols) or _pick_col(cols, COLUMN_ALIASES["email"])
    c_li = _mapped(mapping, "linkedin_url", cols) or _pick_col(cols, COLUMN_ALIASES["linkedin_url"])
    c_site = _mapped(mapping, "website", cols) or _pick_col(cols, COLUMN_ALIASES["website"])

    leads: List[LeadRecord] = []
    for row in reader:
        first = (row.get(c_first) or "").strip() if c_first else ""
        last = (row.get(c_last) or "").strip() if c_last else ""
        name = " ".join([x for x in [first, last] if x]).strip() or "N/D"

        company_name = (row.get(c_company) or "").strip() if c_company else ""
        role = (row.get(c_pos) or "").strip() if c_pos else "N/D"
        email = (row.get(c_email) or "").strip() if c_email else ""
        li = (row.get(c_li) or "").strip() if c_li else ""
        site = (row.get(c_site) or "").strip() if c_site else ""

        if not company_name and name == "N/D":
            continue

        company = CompanyProfile(
            company_name=company_name or "N/D",
            website=site or "",
            province=None,
            industry=None,
            description=None,
            services_products=[],
            target_customers=[],
            technologies=[],
            employees_est=None,
            revenue_est_eur=None,
            headquarters=None,
            recent_projects=[],
            partners=[],
            evidences=[Evidence(title="LinkedIn import", url=li or "", snippet=role or None, source="linkedin")],
        )

        dm = (
            DecisionMaker(name=name, role=role or "N/D", source_url=None, linkedin_url=li or None)
            if name != "N/D"
            else None
        )

        est, _ = estimate_budget(company)

        ve = (
            VerifiedEmail(
                email=email,
                status="unknown",
                source="linkedin_import",
                details={"note": "email non verificata (import)"},
            )
            if email
            else None
        )

        leads.append(
            LeadRecord(
                company=company,
                decision_maker=dm,
                verified_email=ve,
                contact_source="linkedin_import",
                estimated_budget_eur=est,
                investment_window_months=[4, 6],
                score=0,
                score_class="cold",
                status="nuovo",
            )
        )

    return leads
