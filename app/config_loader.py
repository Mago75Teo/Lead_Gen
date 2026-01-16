from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple
import yaml

@dataclass
class FocusConfig:
    raw: Dict[str, Any]

    @property
    def agent_name(self) -> str:
        return self.raw.get("agent", {}).get("name", "Lead Scouting Agent")

    @property
    def reference_company_url(self) -> str:
        return self.raw.get("reference", {}).get("company_url", "")

    @property
    def provinces(self) -> List[str]:
        return list(self.raw.get("reference", {}).get("geography_focus", {}).get("provinces", []))

    @property
    def growth_keywords(self) -> List[str]:
        return list(self.raw.get("lead_scouting", {}).get("growth_signals_keywords", []))

    @property
    def budget_min(self) -> int:
        return int(self.raw.get("lead_scouting", {}).get("min_estimated_budget_eur", 30000))

    @property
    def budget_target(self) -> int:
        return int(self.raw.get("lead_scouting", {}).get("target_budget_eur", 50000))

    @property
    def scoring_weights(self) -> Dict[str, int]:
        return dict(self.raw.get("scoring", {}).get("weights", {}))

    @property
    def score_classes(self) -> Dict[str, Tuple[int, int]]:
        classes = self.raw.get("scoring", {}).get("classes", {})
        out = {}
        for k, v in classes.items():
            out[k] = (int(v[0]), int(v[1]))
        return out

    @property
    def telemetry_enabled(self) -> bool:
        return bool(self.raw.get("telemetry", {}).get("enabled", True))

def load_focus_config(path: str) -> FocusConfig:
    """Load focus config.

    Must be robust on serverless platforms: never crash the whole function on a
    missing file. If a relative path is provided, we resolve it from the project
    root (folder above `app/`).
    """
    p = Path(path)
    if not p.is_absolute():
        project_root = Path(__file__).resolve().parents[1]
        p = (project_root / p).resolve()

    if not p.exists():
        # Fall back to a safe minimal config instead of crashing.
        return FocusConfig(raw={
            "agent": {"name": "Lead Scouting Agent"},
            "reference": {"company_url": ""},
            "lead_scouting": {
                "growth_signals_keywords": [
                    "assunzioni",
                    "lavora con noi",
                    "nuova sede",
                    "ampliamento",
                    "investimento",
                    "commessa",
                    "acquisizione",
                    "funding",
                ],
                "min_estimated_budget_eur": 30000,
                "target_budget_eur": 50000,
            },
            "scoring": {
                "weights": {"fit_settore": 25, "budget": 25, "timing": 25, "crescita": 15, "allineamento": 10},
                "classes": {"hot": [80, 100], "warm": [60, 79], "cold": [0, 59]},
            },
            "telemetry": {"enabled": False},
        })

    raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return FocusConfig(raw=raw)
