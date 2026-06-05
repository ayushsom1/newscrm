"""Renewal risk engine — deterministic.

Inputs:
  days_to_renew     int. Negative = already overdue.
  missed_payments   int >= 0. Count of recent missed cycles.

Output: RenewalSignal{at_risk, severity 'low'|'med'|'high', reasons[]}.

Bands:
  high   overdue OR >= 2 missed payments
  med    expires within 14d OR exactly 1 missed payment
  low    otherwise
"""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class RenewalSignal:
    at_risk: bool
    severity: str  # low | med | high
    reasons: list[str] = field(default_factory=list)


def evaluate_renewal(days_to_renew: int, missed_payments: int) -> RenewalSignal:
    if missed_payments < 0:
        missed_payments = 0

    reasons: list[str] = []
    severity = "low"

    if days_to_renew < 0:
        reasons.append(f"overdue by {-days_to_renew}d")
        severity = "high"
    elif days_to_renew <= 14:
        reasons.append(f"renews in {days_to_renew}d")
        severity = "med"

    if missed_payments >= 2:
        reasons.append(f"{missed_payments} missed payments")
        severity = "high"
    elif missed_payments == 1:
        reasons.append("1 missed payment")
        if severity == "low":
            severity = "med"

    at_risk = severity != "low"
    return RenewalSignal(at_risk=at_risk, severity=severity, reasons=reasons)
