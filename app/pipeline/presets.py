from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Dict, Any
import yaml

@dataclass
class PresetConfig:
    id: str
    name: str
    sender_company: str
    offer_keywords: List[str]
    portfolio_keywords: List[str]
    budget_keyword_boosts: List[Dict[str, Any]]
    email_proof_points: List[str]

def load_preset(preset_id: Optional[str]) -> Optional[PresetConfig]:
    if not preset_id:
        return None
    preset_id = preset_id.strip().lower()
    project_root = Path(__file__).resolve().parents[2]
    path = (project_root / "config" / "presets" / f"{preset_id}.yaml").resolve()
    if not path.exists():
        return None
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    p = raw.get("preset") or {}
    return PresetConfig(
        id=str(p.get("id") or preset_id),
        name=str(p.get("name") or preset_id),
        sender_company=str(p.get("sender_company") or "Teleimpianti S.p.A."),
        offer_keywords=list(p.get("offer_keywords") or []),
        portfolio_keywords=list(p.get("portfolio_keywords") or []),
        budget_keyword_boosts=list(p.get("budget_keyword_boosts") or []),
        email_proof_points=list(p.get("email_proof_points") or []),
    )
