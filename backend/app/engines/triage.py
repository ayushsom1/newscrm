"""Complaint triage engine — deterministic, rule-based.

Two responsibilities:

1. Fallback when the AI is disabled, unreachable, or returns invalid output.
2. Hard guardrail: sensitive complaints (billing/disputes) ALWAYS escalate.
   This applies even if the AI suggested auto-resolve.
"""
from dataclasses import dataclass

AUTO_KEYWORDS = (
    "not delivered", "non-delivery", "non delivery", "no paper",
    "missed", "didn't arrive", "didnt arrive", "did not arrive",
    "pause", "hold", "stop delivery", "vacation",
    "change plan", "plan change", "upgrade plan", "downgrade",
    "address change", "shift", "moved",
    "wet paper", "damaged paper", "torn",
)

# Substring-matched against the lower-cased complaint text. Keep these
# specific — generic words like "complaint", "rude", "bill" matched too
# easily and short-circuited the AI on benign messages. Anything dropped
# from here can still be classified as escalated by the AI itself; the
# list is a guardrail of last resort, not the primary classifier.
ESCALATE_KEYWORDS = (
    "billing dispute", "billing error", "wrong bill", "wrong amount",
    "double charge", "charged twice", "charged me twice",
    "overcharge", "over-charged", "over charged",
    "refund", "chargeback",
    "fraud", "scam", "cheated",
    "lawyer", "legal action", "police", "court", "sue ",
    "harass", "harassment",
    "abusive", "verbal abuse", "threat", "threatened",
)


@dataclass(frozen=True)
class TriageDecision:
    auto: bool
    resolution: str
    reason: str  # short explanation of the rule that fired


def _lc(s: str) -> str:
    return (s or "").lower()


def is_sensitive(text: str) -> bool:
    """Returns True iff the text contains an always-escalate keyword."""
    t = _lc(text)
    return any(k in t for k in ESCALATE_KEYWORDS)


def triage_engine(text: str) -> TriageDecision:
    """Rules-based triage. Sensitive cases escalate; routine ops auto-resolve."""
    t = _lc(text)

    if is_sensitive(t):
        return TriageDecision(
            auto=False,
            resolution="Escalated to a human: complaint references billing/disputes/abuse.",
            reason="sensitive_keyword",
        )

    for kw in AUTO_KEYWORDS:
        if kw in t:
            return TriageDecision(
                auto=True,
                resolution=_routine_resolution_for(kw),
                reason=f"routine_keyword:{kw}",
            )

    # Default: when we can't recognise it, prefer human review over guessing.
    return TriageDecision(
        auto=False,
        resolution="Escalated: complaint does not match a known routine pattern.",
        reason="no_match",
    )


def _routine_resolution_for(keyword: str) -> str:
    if keyword in {"pause", "hold", "stop delivery", "vacation"}:
        return "Paused subscription as requested. Confirmation sent."
    if "address" in keyword or keyword in {"shift", "moved"}:
        return "Address update logged with the distributor."
    if keyword in {"change plan", "plan change", "upgrade plan", "downgrade"}:
        return "Plan change request logged; effective next billing cycle."
    if "wet" in keyword or "damaged" in keyword or "torn" in keyword:
        return "Replacement copy scheduled with the hawker."
    # delivery-failure family
    return "Missed-delivery logged with the hawker; replacement issued."
