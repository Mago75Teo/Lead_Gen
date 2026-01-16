import hashlib
import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from .settings import settings


@dataclass
class TelemetryEvent:
    session_id: str
    event_type: str
    payload: Dict[str, Any]


def _session_hash(session_id: str) -> str:
    raw = f"{settings.TELEMETRY_SALT}:{session_id}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _ensure_parent(path: str) -> None:
    try:
        Path(path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        return


def init_db() -> None:
    """Initialize telemetry DB.

    Must never crash the serverless function: on Vercel the deployment directory is
    read-only; we default to /tmp via settings.
    """
    try:
        if not settings.TELEMETRY_DB_PATH:
            return
        _ensure_parent(settings.TELEMETRY_DB_PATH)
        conn = sqlite3.connect(settings.TELEMETRY_DB_PATH)
        cur = conn.cursor()
        cur.execute(
            """CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                session_hash TEXT NOT NULL,
                event_type TEXT NOT NULL,
                payload_json TEXT NOT NULL
            )"""
        )
        conn.commit()
        conn.close()
    except Exception:
        # Best-effort: telemetry should never break the app
        return


def log_event(ev: TelemetryEvent) -> None:
    """Best-effort telemetry logging."""
    try:
        if not settings.TELEMETRY_DB_PATH:
            return
        _ensure_parent(settings.TELEMETRY_DB_PATH)
        conn = sqlite3.connect(settings.TELEMETRY_DB_PATH)
        cur = conn.cursor()
        ts = datetime.now(timezone.utc).isoformat()
        cur.execute(
            "INSERT INTO events (ts, session_hash, event_type, payload_json) VALUES (?,?,?,?)",
            (ts, _session_hash(ev.session_id), ev.event_type, json.dumps(ev.payload, ensure_ascii=False)),
        )
        conn.commit()
        conn.close()
    except Exception:
        return
