"""Classified pricing engine — deterministic.

Inputs:
  words           int, number of words in the ad.
  category        one of CATEGORIES.
  duration_days   int >= 1, how many days the ad runs.
  locale          "IN" (₹/GST) or "NP" (NPR/VAT).

Output: Quote{net, gst, total, currency, breakdown}.

Rules:
  - First 20 words = base_rate (per insertion-day).
  - Every additional word adds extra_per_word (per insertion-day).
  - Some categories have a category multiplier (premium placement).
  - Multi-day discount tiers (>=7d, >=14d, >=30d).
  - GST/VAT applied on the discounted net.

Money is ``Decimal`` end to end, ROUND_HALF_UP, 2dp.
"""
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

TWO = Decimal("0.01")
ZERO = Decimal("0")

Locale = Literal["IN", "NP"]

CATEGORIES: dict[str, Decimal] = {
    "GENERAL": Decimal("1.00"),
    "MATRIMONIAL": Decimal("1.20"),
    "PROPERTY": Decimal("1.30"),
    "JOBS": Decimal("1.15"),
    "OBITUARY": Decimal("0.90"),
    "VEHICLES": Decimal("1.10"),
}

LOCALES: dict[Locale, dict] = {
    "IN": {
        "currency": "INR",
        "tax_label": "GST",
        "tax_rate": Decimal("0.05"),  # 5%
        "base_rate": Decimal("250.00"),
        "extra_per_word": Decimal("12.00"),
        "base_words": 20,
    },
    "NP": {
        "currency": "NPR",
        "tax_label": "VAT",
        "tax_rate": Decimal("0.13"),  # 13%
        "base_rate": Decimal("220.00"),
        "extra_per_word": Decimal("10.00"),
        "base_words": 20,
    },
}


@dataclass(frozen=True)
class Quote:
    currency: str
    tax_label: str
    net: Decimal
    tax: Decimal
    total: Decimal
    breakdown: dict[str, str]


def _q(d: Decimal) -> Decimal:
    return d.quantize(TWO, rounding=ROUND_HALF_UP)


def _discount(days: int) -> Decimal:
    if days >= 30:
        return Decimal("0.20")
    if days >= 14:
        return Decimal("0.10")
    if days >= 7:
        return Decimal("0.05")
    return ZERO


def quote(
    words: int,
    category: str,
    duration_days: int,
    locale: Locale = "IN",
) -> Quote:
    if words < 1:
        raise ValueError("words must be >= 1")
    if duration_days < 1:
        raise ValueError("duration_days must be >= 1")
    if locale not in LOCALES:
        raise ValueError(f"unknown locale: {locale}")
    cat = category.upper()
    if cat not in CATEGORIES:
        raise ValueError(f"unknown category: {category}")

    cfg = LOCALES[locale]
    mult = CATEGORIES[cat]
    base_rate: Decimal = cfg["base_rate"]
    extra_per_word: Decimal = cfg["extra_per_word"]
    base_words: int = cfg["base_words"]
    tax_rate: Decimal = cfg["tax_rate"]

    extra_words = max(0, words - base_words)
    per_day = (base_rate + Decimal(extra_words) * extra_per_word) * mult

    gross = per_day * Decimal(duration_days)
    disc = _discount(duration_days)
    net = _q(gross * (Decimal("1") - disc))
    tax = _q(net * tax_rate)
    total = _q(net + tax)

    return Quote(
        currency=cfg["currency"],
        tax_label=cfg["tax_label"],
        net=net,
        tax=tax,
        total=total,
        breakdown={
            "category_multiplier": str(mult),
            "per_day": str(_q(per_day)),
            "days": str(duration_days),
            "gross": str(_q(gross)),
            "discount_pct": str(disc * 100),
            "tax_rate_pct": str(tax_rate * 100),
        },
    )
