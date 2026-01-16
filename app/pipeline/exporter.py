from __future__ import annotations

from typing import List, Dict, Any, Tuple
from datetime import datetime
from pathlib import Path
import csv
import io
import os

from openpyxl import Workbook

from ..models import LeadRecord

# Serverless-friendly: write to /tmp by default (Vercel / AWS Lambda)
EXPORT_DIR = Path(os.environ.get("EXPORT_DIR", "/tmp/exports"))

MIME_BY_FORMAT = {
    "csv": "text/csv; charset=utf-8",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


def _rows(leads: List[LeadRecord]) -> Tuple[List[str], List[Dict[str, Any]]]:
    rows: List[Dict[str, Any]] = []
    for l in leads:
        c = l.company
        dm = l.decision_maker
        ve = l.verified_email
        rows.append(
            {
                "Azienda": c.company_name,
                "Sito": c.website,
                "Settore": c.industry,
                "Provincia": c.province,
                "Dimensione_dipendenti": c.employees_est,
                "Fatturato_EUR": c.revenue_est_eur,
                "Trigger_crescita": " | ".join(c.recent_projects or []),
                "Fonti_trigger": " | ".join([e.url for e in (c.evidences or [])[:5]]),
                "Budget_stimato_EUR": l.estimated_budget_eur,
                "Timing_investimento": "-".join(map(str, l.investment_window_months or [])),
                "Decision_maker": (dm.name if dm else None),
                "Ruolo": (dm.role if dm else None),
                "Email_verificata": (ve.email if ve else None),
                "Stato_email": (ve.status if ve else None),
                "Fonte_contatto": l.contact_source,
                "Score": l.score,
                "Classe": l.score_class,
                "Stato": l.status,
            }
        )

    headers = list(rows[0].keys()) if rows else [
        "Azienda",
        "Sito",
        "Settore",
        "Provincia",
        "Dimensione_dipendenti",
        "Fatturato_EUR",
        "Trigger_crescita",
        "Fonti_trigger",
        "Budget_stimato_EUR",
        "Timing_investimento",
        "Decision_maker",
        "Ruolo",
        "Email_verificata",
        "Stato_email",
        "Fonte_contatto",
        "Score",
        "Classe",
        "Stato",
    ]
    return headers, rows


def export_leads_bytes(leads: List[LeadRecord], file_format: str = "xlsx") -> Tuple[bytes, str, str]:
    """Create an XLSX/CSV export in memory (serverless-safe)."""
    fmt = (file_format or "xlsx").lower()
    if fmt not in ("xlsx", "csv"):
        fmt = "xlsx"

    headers, rows = _rows(leads)

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    fname = f"leads_{ts}.{fmt}"
    mime = MIME_BY_FORMAT[fmt]

    if fmt == "csv":
        sio = io.StringIO()
        writer = csv.DictWriter(sio, fieldnames=headers)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in headers})
        return sio.getvalue().encode("utf-8-sig"), fname, mime

    wb = Workbook()
    ws = wb.active
    ws.title = "Leads"
    ws.append(headers)
    for r in rows:
        ws.append([r.get(h) for h in headers])

    bio = io.BytesIO()
    wb.save(bio)
    return bio.getvalue(), fname, mime


def export_leads(leads: List[LeadRecord], file_format: str = "xlsx") -> Dict[str, Any]:
    """Best-effort file export to the filesystem (defaults to /tmp)."""
    content, fname, mime = export_leads_bytes(leads, file_format=file_format)
    try:
        EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        path = EXPORT_DIR / fname
        path.write_bytes(content)
        return {"file": fname, "path": str(path), "mime": mime}
    except Exception:
        # Still return something useful even if FS write fails
        return {"file": fname, "path": None, "mime": mime}
