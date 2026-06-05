"""Print-run forecast engine — deterministic.

For each area, target copies are computed from active subscribers plus a small
buffer for newsstand sales, then increased to cover historical returns.

Inputs:
  active_subs       int >= 0
  newsstand_buffer  int >= 0  (extra copies routinely sold off the stand)
  returns_pct       float 0..100  (historical % unsold to compensate for)

Output: PrintRun{base, buffer, returns_factor, target}

target = round((base + buffer) * (1 + returns_pct/100))
"""
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal


@dataclass(frozen=True)
class PrintRun:
    base: int
    buffer: int
    returns_pct: float
    target: int


def forecast_print_run(
    active_subs: int, newsstand_buffer: int = 0, returns_pct: float = 0.0
) -> PrintRun:
    if active_subs < 0:
        active_subs = 0
    if newsstand_buffer < 0:
        newsstand_buffer = 0
    returns_pct = max(0.0, min(100.0, returns_pct))

    base_total = Decimal(active_subs + newsstand_buffer)
    factor = Decimal("1") + (Decimal(str(returns_pct)) / Decimal("100"))
    target = int((base_total * factor).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    return PrintRun(
        base=active_subs,
        buffer=newsstand_buffer,
        returns_pct=returns_pct,
        target=target,
    )
