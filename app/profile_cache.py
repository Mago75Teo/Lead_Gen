from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Any, Dict
import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone

IS_VERCEL = os.getenv("VERCEL") == "1" or bool(os.getenv("VERCEL_ENV"))
DEFAULT_DB_PATH = os.environ.get("PROFILE_CACHE_DB_PATH") or ("/tmp/profile_cache.sqlite3" if IS_VERCEL else "./data/profile_cache.sqlite3")
DEFAULT_TTL_DAYS = int(os.environ.get("PROFILE_CACHE_TTL_DAYS", "183"))  # ~6 months


@dataclass
class CacheResult:
    hit: bool
    value: Optional[Dict[str, Any]] = None


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_dir(path: str) -> None:
    d = os.path.dirname(os.path.abspath(path))
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)


def _connect(path: str) -> sqlite3.Connection:
    _ensure_dir(path)
    conn = sqlite3.connect(path, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS project_profiles (
            reference_url TEXT PRIMARY KEY,
            profile_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        )"""
    )
    return conn


def _is_fresh(created_at_iso: str, ttl_days: int) -> bool:
    try:
        created = datetime.fromisoformat(created_at_iso.replace("Z", "+00:00"))
    except Exception:
        return False
    return created >= (_utcnow() - timedelta(days=ttl_days))


def get_profile(reference_url: str, db_path: str = DEFAULT_DB_PATH, ttl_days: int = DEFAULT_TTL_DAYS) -> CacheResult:
    """Return cached profile if present and not older than ttl_days."""
    try:
        conn = _connect(db_path)
        try:
            row = conn.execute(
                "SELECT profile_json, created_at FROM project_profiles WHERE reference_url = ?",
                (reference_url,),
            ).fetchone()
            if not row:
                return CacheResult(hit=False)
            profile_json, created_at = row
            if not _is_fresh(created_at, ttl_days):
                conn.execute("DELETE FROM project_profiles WHERE reference_url = ?", (reference_url,))
                conn.commit()
                return CacheResult(hit=False)
            return CacheResult(hit=True, value=json.loads(profile_json))
        finally:
            conn.close()
    except Exception:
        return CacheResult(hit=False)


def set_profile(reference_url: str, profile: Dict[str, Any], db_path: str = DEFAULT_DB_PATH) -> None:
    try:
        conn = _connect(db_path)
        try:
            conn.execute(
                "INSERT OR REPLACE INTO project_profiles(reference_url, profile_json, created_at) VALUES (?, ?, ?)",
                (reference_url, json.dumps(profile, ensure_ascii=False), _utcnow().isoformat().replace("+00:00", "Z")),
            )
            conn.commit()
        finally:
            conn.close()
    except Exception:
        return


def purge_expired(db_path: str = DEFAULT_DB_PATH, ttl_days: int = DEFAULT_TTL_DAYS) -> int:
    """Delete expired cached profiles. Returns number of deleted rows (best effort)."""
    try:
        conn = _connect(db_path)
        try:
            cutoff = (_utcnow() - timedelta(days=ttl_days)).isoformat().replace("+00:00", "Z")
            cur = conn.execute("SELECT COUNT(*) FROM project_profiles WHERE created_at < ?", (cutoff,))
            n = int(cur.fetchone()[0] or 0)
            conn.execute("DELETE FROM project_profiles WHERE created_at < ?", (cutoff,))
            conn.commit()
            return n
        finally:
            conn.close()
    except Exception:
        return 0


def delete_profile(reference_url: str, db_path: str = DEFAULT_DB_PATH) -> None:
    try:
        conn = _connect(db_path)
        try:
            conn.execute("DELETE FROM project_profiles WHERE reference_url = ?", (reference_url,))
            conn.commit()
        finally:
            conn.close()
    except Exception:
        return


def flush_cache(db_path: str = DEFAULT_DB_PATH) -> int:
    """Delete all cached profiles. Returns number of deleted rows (best effort)."""
    try:
        conn = _connect(db_path)
        try:
            cur = conn.execute("SELECT COUNT(*) FROM project_profiles")
            n = int(cur.fetchone()[0] or 0)
            conn.execute("DELETE FROM project_profiles")
            conn.commit()
            return n
        finally:
            conn.close()
    except Exception:
        return 0
