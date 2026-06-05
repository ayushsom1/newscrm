"""Churn engine — deterministic.

Inputs:
  spend_trend       YoY % change. -100..+inf. Negative = shrinking.
  open_rate         Proposal open rate, 0..100.
  days_to_expiry    Days until the active contract expires. None = no contract.

Output: ChurnResult{score 0..100, band low|med|high, reasons[]}.
Higher score = more likely to churn.

Bands:
  0..39  low
  40..69 med
  70..100 high
"""
from dataclasses import dataclass, field

BAND_LOW = "low"
BAND_MED = "med"
BAND_HIGH = "high"


@dataclass(frozen=True)
class ChurnResult:
    score: int
    band: str
    reasons: list[str] = field(default_factory=list)


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _band(score: int) -> str:
    if score >= 70:
        return BAND_HIGH
    if score >= 40:
        return BAND_MED
    return BAND_LOW


def score_churn(
    spend_trend: float,
    open_rate: float,
    days_to_expiry: int | None,
) -> ChurnResult:
    reasons: list[str] = []

    # Spend trend: -100 (collapse) -> 60 pts, 0 -> 0 pts, +100 (growth) -> -20 pts
    # Map linearly with clamp.
    st = _clamp(spend_trend, -100.0, 100.0)
    if st <= 0:
        spend_pts = (-st / 100.0) * 60.0
    else:
        spend_pts = -(st / 100.0) * 20.0
    if st <= -10:
        reasons.append(f"spend down {st:.1f}%")

    # Open rate: 0 -> 25 pts, 100 -> 0 pts (linear inverse).
    orate = _clamp(open_rate, 0.0, 100.0)
    open_pts = (1.0 - orate / 100.0) * 25.0
    if orate < 30:
        reasons.append(f"low proposal open rate ({orate:.0f}%)")

    # Days to expiry: <=0 (already expired) -> 25, 0..30 -> 25..10, 30..90 -> 10..0, >90 -> 0
    if days_to_expiry is None:
        expiry_pts = 15.0
        reasons.append("no active contract")
    elif days_to_expiry <= 0:
        expiry_pts = 25.0
        reasons.append("contract expired")
    elif days_to_expiry <= 30:
        # 0d -> 25, 30d -> 10
        expiry_pts = 25.0 - (days_to_expiry / 30.0) * 15.0
        reasons.append(f"expires in {days_to_expiry}d")
    elif days_to_expiry <= 90:
        # 30d -> 10, 90d -> 0
        expiry_pts = 10.0 - ((days_to_expiry - 30) / 60.0) * 10.0
    else:
        expiry_pts = 0.0

    raw = spend_pts + open_pts + expiry_pts
    score = int(round(_clamp(raw, 0.0, 100.0)))
    return ChurnResult(score=score, band=_band(score), reasons=reasons)
