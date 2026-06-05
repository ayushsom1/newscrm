"""AI-assisted complaint triage.

Flow:
  1. Try the model with a tight, grounded prompt.
  2. Validate the response against TriageAIOut (Pydantic).
  3. Override `auto=True` to False if the text matches our sensitive list —
     the LLM is never allowed to override the human-only rule.
  4. On any failure (disabled / transport / non-JSON / validation), fall back
     to the deterministic engine.
  5. Caller writes the AuditLog with the resulting source ("AI" or "ENGINE").
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from pydantic import BaseModel, Field

from app.ai.client import AIClientError, AIDisabledError, chat_json
from app.engines.triage import is_sensitive, triage_engine
from app.services.autonomy import get_autonomy

log = logging.getLogger(__name__)


class TriageAIOut(BaseModel):
    auto: bool = Field(description="True if a routine ops action can resolve it")
    resolution: str = Field(min_length=1, max_length=400)
    category: str | None = Field(default=None, max_length=40)


@dataclass(frozen=True)
class TriageResult:
    auto: bool
    resolution: str
    source: str  # "AI" or "ENGINE"
    reason: str  # short tag for audit


SYSTEM_PROMPT = """You triage newspaper subscriber complaints for a regional CRM.

Output JSON ONLY with this shape:
  {"auto": bool, "resolution": "string under 400 chars", "category": "string|null"}

Rules:
- `auto: true` ONLY for routine ops the desk can handle: non-delivery,
  paused/resumed delivery, address changes, plan changes, replacement of
  damaged copy.
- `auto: false` for anything billing, refunds, disputes, fraud, legal,
  abuse, or unclear/sensitive. When in doubt, escalate.
- `resolution` is a short action statement to log against the complaint
  (e.g. "Missed-delivery logged; replacement scheduled with hawker.").
- Do NOT invent customer names or subscription IDs.
- Do NOT compute money, refunds, or prices.
"""


def triage_complaint(text: str) -> TriageResult:
    """Triage a single complaint. Never raises — always returns a result."""
    autonomy = get_autonomy()

    # First: hard sensitive-keyword check; we don't even ask the LLM about these.
    if is_sensitive(text):
        engine = triage_engine(text)
        return TriageResult(
            auto=False,
            resolution=engine.resolution,
            source="ENGINE",
            reason=engine.reason,
        )

    # Admin dial: AI completely off -> engine fallback.
    if not autonomy.triage_ai_enabled:
        engine = triage_engine(text)
        return TriageResult(
            auto=engine.auto and autonomy.triage_auto_resolve_enabled,
            resolution=engine.resolution,
            source="ENGINE",
            reason=f"autonomy_ai_off:{engine.reason}",
        )

    try:
        ai_out, _meta = chat_json(
            TriageAIOut,
            system=SYSTEM_PROMPT,
            user=f"Complaint text:\n\"\"\"\n{text.strip()}\n\"\"\"",
            max_tokens=300,
            temperature=0.1,
        )
    except AIDisabledError:
        engine = triage_engine(text)
        return TriageResult(
            auto=engine.auto,
            resolution=engine.resolution,
            source="ENGINE",
            reason=f"ai_disabled:{engine.reason}",
        )
    except AIClientError as e:
        log.warning("AI triage failed, falling back to engine: %s", e)
        engine = triage_engine(text)
        return TriageResult(
            auto=engine.auto,
            resolution=engine.resolution,
            source="ENGINE",
            reason=f"ai_error:{engine.reason}",
        )

    # Even if AI said auto=True, a sensitive-keyword check would have caught it
    # above. As a defence-in-depth: cap auto with the sensitive check AND the
    # admin dial. If auto-resolve is disabled, AI suggestions still classify,
    # but everything routes to a human.
    auto = (
        ai_out.auto
        and not is_sensitive(text)
        and autonomy.triage_auto_resolve_enabled
    )
    return TriageResult(
        auto=auto,
        resolution=ai_out.resolution.strip(),
        source="AI",
        reason="ai_classified",
    )
