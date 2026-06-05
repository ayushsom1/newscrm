"""AI proposal drafting.

Grounding: we build a compact JSON snapshot of the advertiser (+ active
contracts + churn) and pass it to the model. The system prompt forbids the
model from inventing prices, dates, or other numbers — it can only restate
what's in the snapshot.

We do NOT ask for structured JSON output here, because the proposal body is
prose by nature. The "subject" line is parsed from the first line.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from pydantic import BaseModel

from app.ai.client import AIClientError, AIDisabledError, ChatResult, chat
from app.models.advertiser import Advertiser, ContractStatus
from app.services.autonomy import get_autonomy

log = logging.getLogger(__name__)


SYSTEM_PROMPT = """You draft renewal/sales proposals for a regional newspaper CRM.

You will be given a JSON snapshot of one advertiser. Write a short, plain
business email to the advertiser proposing a renewal or upgrade.

Rules:
- First line: "Subject: ..." — a one-line subject (no quotes).
- Body: 3-6 short paragraphs, plain text, no markdown headings.
- Tone: warm, factual, sales-professional. No emojis, no hype.
- DO NOT invent numbers (rates, percentages, money, dates). You may restate
  the values present in the snapshot.
- DO NOT promise discounts unless `proposed_discount_pct` is in the snapshot.
- Mention any specific churn signals (e.g. "we noticed open rates have
  dipped") only if `churn.reasons` is non-empty.
- Sign off as "the News CRM team".

The proposal is a DRAFT; a human will review before it is sent. Do not
include placeholders like [NAME] — use the advertiser name from the snapshot.
"""


@dataclass(frozen=True)
class DraftedProposal:
    subject: str
    body: str
    model_used: str
    needs_human: bool
    needs_human_reason: str | None


class _SnapshotChurn(BaseModel):
    score: int | None
    band: str | None
    reasons: list[str] = []


class _SnapshotContract(BaseModel):
    end_date: str
    value: str
    slots: int


class AdvertiserSnapshot(BaseModel):
    """Compact, read-only grounding for the drafter. Numbers as strings to avoid
    locale ambiguity in the prompt."""

    name: str
    category: str | None
    contact_name: str | None
    contact_email: str | None
    annual_value: str
    spend_trend_pct: str
    proposal_open_rate_pct: str
    churn: _SnapshotChurn
    active_contracts: list[_SnapshotContract]


def build_snapshot(adv: Advertiser, churn_reasons: list[str]) -> AdvertiserSnapshot:
    active = [c for c in adv.contracts if c.status == ContractStatus.ACTIVE]
    return AdvertiserSnapshot(
        name=adv.name,
        category=adv.category,
        contact_name=adv.contact_name,
        contact_email=adv.contact_email,
        annual_value=str(Decimal(adv.annual_value or 0)),
        spend_trend_pct=str(Decimal(adv.spend_trend or 0)),
        proposal_open_rate_pct=str(Decimal(adv.proposal_open_rate or 0)),
        churn=_SnapshotChurn(
            score=adv.churn_score,
            band=adv.churn_band,
            reasons=churn_reasons,
        ),
        active_contracts=[
            _SnapshotContract(
                end_date=str(c.end_date),
                value=str(Decimal(c.value)),
                slots=int(c.slots or 0),
            )
            for c in active
        ],
    )


def _parse_subject(text: str) -> tuple[str, str]:
    text = text.strip()
    if text.lower().startswith("subject:"):
        head, _, rest = text.partition("\n")
        subject = head.split(":", 1)[1].strip()
        body = rest.strip()
        if subject and body:
            return subject, body
    # Fall back: synthesise a subject from the first sentence.
    first_line = text.splitlines()[0].strip()
    subject = (first_line[:80] + "…") if len(first_line) > 80 else first_line
    return subject, text


def _engine_template(adv: Advertiser) -> tuple[str, str]:
    """Last-resort prose draft if the model is unavailable. Deterministic."""
    subject = f"Renewal proposal — {adv.name}"
    lines = [
        f"Dear {adv.contact_name or adv.name},",
        "",
        "Thank you for partnering with us. We are putting together a renewal "
        "proposal for the next cycle and wanted to share an initial draft for "
        "your consideration.",
    ]
    if adv.churn_band == "high":
        lines += [
            "",
            "We have noticed some softening signals on your account and would "
            "like to find time this week to review options together. Please "
            "treat this note as a starting point.",
        ]
    lines += [
        "",
        "A member of our team will follow up to confirm the terms and answer "
        "any questions. We appreciate your continued business.",
        "",
        "Warm regards,",
        "the News CRM team",
    ]
    return subject, "\n".join(lines)


def draft_proposal(adv: Advertiser, churn_reasons: list[str]) -> DraftedProposal:
    """Try the AI model, fall back to a deterministic template on any failure.

    High-churn accounts always get `needs_human=True` (when the dial says so).
    The admin "dial" can disable AI drafting entirely; we then use the
    engine template and flag it for review.
    """
    autonomy = get_autonomy()
    snapshot = build_snapshot(adv, churn_reasons)
    user_msg = (
        "Advertiser snapshot:\n"
        + snapshot.model_dump_json(indent=2)
        + f"\n\nToday is {datetime.now(timezone.utc).date()}."
    )

    needs_human = (
        adv.churn_band == "high" and autonomy.high_churn_always_needs_human
    )
    needs_human_reason = (
        "high churn — sales lead must review before send"
        if needs_human else None
    )

    if not autonomy.ai_draft_enabled:
        subject, body = _engine_template(adv)
        return DraftedProposal(
            subject=subject,
            body=body,
            model_used="ENGINE_AUTONOMY_OFF",
            needs_human=True,
            needs_human_reason=needs_human_reason
            or "AI drafting is disabled in Settings; please review",
        )

    try:
        result: ChatResult = chat(
            system=SYSTEM_PROMPT,
            user=user_msg,
            max_tokens=600,
            temperature=0.4,
        )
        subject, body = _parse_subject(result.content)
        return DraftedProposal(
            subject=subject,
            body=body,
            model_used=result.model,
            needs_human=needs_human,
            needs_human_reason=needs_human_reason,
        )
    except (AIDisabledError, AIClientError) as e:
        log.warning("AI drafter failed, using engine template: %s", e)
        subject, body = _engine_template(adv)
        return DraftedProposal(
            subject=subject,
            body=body,
            model_used="ENGINE_FALLBACK",
            needs_human=True,  # always require review when we used the template
            needs_human_reason=needs_human_reason
            or "engine fallback was used — please review",
        )
