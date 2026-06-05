from decimal import Decimal

import pytest

from app.engines.pricing import quote


def test_base_quote_india_general_one_day() -> None:
    q = quote(words=20, category="GENERAL", duration_days=1, locale="IN")
    # 20 words = base only -> 250.00, no discount, 5% GST
    assert q.net == Decimal("250.00")
    assert q.tax == Decimal("12.50")
    assert q.total == Decimal("262.50")
    assert q.currency == "INR"
    assert q.tax_label == "GST"


def test_extra_words_charge_per_day() -> None:
    # 25 words = 5 extra * 12 = 60. per_day = 310. 3 days = 930.
    q = quote(words=25, category="GENERAL", duration_days=3, locale="IN")
    assert q.net == Decimal("930.00")
    assert q.tax == Decimal("46.50")
    assert q.total == Decimal("976.50")


def test_category_multiplier_property() -> None:
    g = quote(words=20, category="GENERAL", duration_days=1, locale="IN")
    p = quote(words=20, category="PROPERTY", duration_days=1, locale="IN")
    assert p.net > g.net
    # property multiplier = 1.30 -> 250 * 1.30 = 325.00
    assert p.net == Decimal("325.00")


def test_weekly_discount_applied() -> None:
    # 7 days @ base 250 = 1750. 5% off = 1662.50
    q = quote(words=20, category="GENERAL", duration_days=7, locale="IN")
    assert q.net == Decimal("1662.50")
    # 30+ days = 20% off
    q30 = quote(words=20, category="GENERAL", duration_days=30, locale="IN")
    assert q30.net == Decimal("6000.00")  # 7500 * 0.80


def test_nepal_locale_uses_vat_and_npr() -> None:
    q = quote(words=20, category="GENERAL", duration_days=1, locale="NP")
    assert q.currency == "NPR"
    assert q.tax_label == "VAT"
    assert q.net == Decimal("220.00")
    # 13% VAT
    assert q.tax == Decimal("28.60")
    assert q.total == Decimal("248.60")


def test_rounding_half_up_two_dp() -> None:
    # contrived inputs that produce non-trivial fractions
    q = quote(words=21, category="OBITUARY", duration_days=1, locale="IN")
    # 1 extra word * 12 = 12; per_day = (250+12) * 0.90 = 235.80
    assert q.net == Decimal("235.80")
    assert q.tax == Decimal("11.79")
    assert q.total == Decimal("247.59")


def test_invalid_inputs_raise() -> None:
    with pytest.raises(ValueError):
        quote(words=0, category="GENERAL", duration_days=1, locale="IN")
    with pytest.raises(ValueError):
        quote(words=10, category="GENERAL", duration_days=0, locale="IN")
    with pytest.raises(ValueError):
        quote(words=10, category="UNKNOWN", duration_days=1, locale="IN")
    with pytest.raises(ValueError):
        quote(words=10, category="GENERAL", duration_days=1, locale="US")  # type: ignore[arg-type]


def test_quote_is_deterministic() -> None:
    a = quote(words=37, category="MATRIMONIAL", duration_days=14, locale="IN")
    b = quote(words=37, category="MATRIMONIAL", duration_days=14, locale="IN")
    assert a == b
