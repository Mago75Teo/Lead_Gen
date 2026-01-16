#!/usr/bin/env python3
from __future__ import annotations
import asyncio
import json
from app.config_loader import load_focus_config
from app.models import RunRequest, Geography, Segment
from app.pipeline.orchestrator import run_pipeline

async def main():
    focus = load_focus_config("config/focus.yaml")
    req = RunRequest(
        reference_company_url=focus.reference_company_url,
        geography=Geography(country="Italia", region="Emilia-Romagna", provinces=focus.provinces),
        industry="produzione",
        segment=Segment(type="PMI", employees_min=50, employees_max=500),
        investment_window_months=[4,6],
        allowed_channels=["email"],
        limit=20,
        include_email_drafts=False,
        session_id="cli",
    )
    res = await run_pipeline(req, focus)
    # Print summary
    print(json.dumps({
        "run_id": res["run_id"],
        "leads": len(res["leads"]),
        "export": res.get("export"),
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
