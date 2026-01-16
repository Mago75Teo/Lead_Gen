from __future__ import annotations
from typing import List, Dict, Any
import uuid

from ..models import RunRequest, LeadRecord, Evidence
from ..config_loader import FocusConfig
from .discover import discover_candidates
from .enrich import enrich_candidates
from .identify import identify_for_companies
from .verify import verify_leads
from .score import score_leads
from .exporter import export_leads
from .email_drafts import generate_email_drafts
from .budget import estimate_budget
from .project_profile import build_project_profile
from .presets import load_preset

async def run_pipeline(req: RunRequest, focus: FocusConfig) -> Dict[str, Any]:
    run_id = uuid.uuid4().hex[:12]
    preset_cfg = load_preset(req.preset)

    project_profile = None
    if getattr(req, "enable_project_profile", True) and req.reference_company_url:
        try:
            project_profile = await build_project_profile(
                req.reference_company_url,
                req.api_keys,
                force_refresh=req.force_refresh_profile,
            )
        except Exception:
            project_profile = None

    candidates = await discover_candidates(
        focus=focus,
        industry=req.industry,
        geo=req.geography,
        segment=req.segment,
        limit=req.limit,
        api_keys=req.api_keys,
        preset=preset_cfg,
    )
    companies = await enrich_candidates(candidates)

    pairs = await identify_for_companies(companies)
    leads: List[LeadRecord] = []
    for comp, dm in pairs:
        est, rationale = estimate_budget(comp, project_profile=project_profile, preset=preset_cfg)
        comp.evidences = (comp.evidences or []) + [
            Evidence(title="budget_estimate", url=comp.website, snippet=rationale, source="heuristic")
        ]
        leads.append(LeadRecord(
            company=comp,
            decision_maker=dm,
            verified_email=None,
            contact_source=None,
            estimated_budget_eur=est,
            investment_window_months=req.investment_window_months,
            score=0,
            score_class="cold",
            status="nuovo",
        ))

    leads = await verify_leads(leads, api_keys=req.api_keys)
    leads = score_leads(leads, focus, project_profile=project_profile, preset=preset_cfg)

    export_info = {"file_format": "xlsx", "download_url": "/export/download"}

    drafts = []
    if req.include_email_drafts:
        drafts = await generate_email_drafts(leads, api_keys=req.api_keys, project_profile=project_profile, preset=preset_cfg)

    return {
        "run_id": run_id,
        "preset": (preset_cfg.id if preset_cfg else None),
        "project_profile": project_profile,
        "leads": leads,
        "export": export_info,
        "email_drafts": drafts,
    }
