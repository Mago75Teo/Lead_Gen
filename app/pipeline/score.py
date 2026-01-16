from __future__ import annotations
from typing import List, Dict
from ..models import LeadRecord
from ..config_loader import FocusConfig

def _clamp(x: float, a: float, b: float) -> float:
    return max(a, min(b, x))

def classify(score: int, classes: Dict[str, tuple[int, int]]) -> str:
    for name, (lo, hi) in classes.items():
        if lo <= score <= hi:
            return name
    return "cold"

def score_leads(leads: List[LeadRecord], focus: FocusConfig, project_profile=None, preset=None) -> List[LeadRecord]:
    w = focus.scoring_weights
    classes = focus.score_classes

    # Reference keywords from Project Profile + Preset
    ref_kw = set()
    if project_profile:
        for s in (getattr(project_profile, "services_offered", []) or []):
            if isinstance(s, str) and s.strip():
                ref_kw.add(s.lower())
        for s in (getattr(project_profile, "technologies", []) or []):
            if isinstance(s, str) and s.strip():
                ref_kw.add(s.lower())
        for s in (getattr(project_profile, "industries_served", []) or []):
            if isinstance(s, str) and s.strip():
                ref_kw.add(s.lower())
    if preset and getattr(preset, "portfolio_keywords", None):
        for s in preset.portfolio_keywords:
            if isinstance(s, str) and s.strip():
                ref_kw.add(s.lower())

    for lead in leads:
        fit_settore = 0
        capacita_budget = 0
        timing = 0
        crescita = 0
        allineamento = 0

        # Fit settore
        if lead.company.industry:
            fit_settore = w.get("fit_settore", 25)

        # Budget
        if lead.estimated_budget_eur:
            if lead.estimated_budget_eur >= 100000:
                capacita_budget = w.get("capacita_budget", 25)
            elif lead.estimated_budget_eur >= focus.budget_target:
                capacita_budget = w.get("capacita_budget", 25)
            elif lead.estimated_budget_eur >= focus.budget_min:
                capacita_budget = int(w.get("capacita_budget", 25) * 0.7)
            else:
                capacita_budget = int(w.get("capacita_budget", 25) * 0.3)
        else:
            capacita_budget = int(w.get("capacita_budget", 25) * 0.5)

        # Timing investimento
        if lead.investment_window_months:
            lo, hi = min(lead.investment_window_months), max(lead.investment_window_months)
            if lo <= 6 and hi >= 4:
                timing = w.get("timing_investimento", 25)
            else:
                timing = int(w.get("timing_investimento", 25) * 0.5)
        else:
            timing = int(w.get("timing_investimento", 25) * 0.5)

        # Segnali crescita
        evid_n = len(lead.company.evidences or [])
        crescita = int(_clamp(evid_n / 5.0, 0, 1) * w.get("segnali_crescita", 15))

        # Allineamento portfolio (baseline: presenza servizi)
        overlap_base = min(len(lead.company.services_products or []), 10) / 10.0
        allineamento = int(_clamp(overlap_base, 0, 1) * w.get("allineamento_referenze", 10))

        # Allineamento portfolio via keywords (Project Profile / Preset)
        if ref_kw:
            comp_kw = set()
            for s in (lead.company.services_products or []):
                if isinstance(s, str) and s.strip():
                    comp_kw.add(s.lower())
            for s in (lead.company.technologies or []):
                if isinstance(s, str) and s.strip():
                    comp_kw.add(s.lower())
            if lead.company.industry:
                comp_kw.add(str(lead.company.industry).lower())

            ov = len(ref_kw.intersection(comp_kw))
            w_align = w.get("allineamento_referenze", 10)
            if ov >= 6:
                allineamento = w_align
            elif ov >= 3:
                allineamento = max(allineamento, int(w_align * 0.7))
            elif ov >= 1:
                allineamento = max(allineamento, int(w_align * 0.4))

        total = fit_settore + capacita_budget + timing + crescita + allineamento
        lead.score = int(_clamp(total, 0, 100))
        lead.score_class = classify(lead.score, classes)

    return leads
