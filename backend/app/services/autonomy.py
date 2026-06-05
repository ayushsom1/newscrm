"""Cached accessor for the AutonomyConfig singleton.

Reads are hot-pathed (triage + drafter call this on every model invocation).
We cache the row in-process for 30s; a Settings update sets _cache=None to
invalidate immediately.
"""
from __future__ import annotations

import time
from threading import Lock

from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models.settings import SINGLETON_ID, AutonomyConfig

_CACHE: AutonomyConfig | None = None
_CACHE_AT: float = 0.0
_TTL = 30.0
_LOCK = Lock()


def _load(db: Session) -> AutonomyConfig:
    row = db.get(AutonomyConfig, SINGLETON_ID)
    if row is None:
        # Defensive: if the migration seed somehow got removed, create it.
        row = AutonomyConfig(id=SINGLETON_ID)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def get_autonomy() -> AutonomyConfig:
    """Returns a detached snapshot of the autonomy row. Safe to read fields,
    but do not mutate."""
    global _CACHE, _CACHE_AT
    with _LOCK:
        if _CACHE is not None and (time.monotonic() - _CACHE_AT) < _TTL:
            return _CACHE
        with SessionLocal() as db:
            row = _load(db)
            db.expunge(row)
        _CACHE = row
        _CACHE_AT = time.monotonic()
        return row


def invalidate_cache() -> None:
    global _CACHE, _CACHE_AT
    with _LOCK:
        _CACHE = None
        _CACHE_AT = 0.0
