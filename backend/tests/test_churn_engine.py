from app.engines.churn import (
    BAND_HIGH,
    BAND_LOW,
    BAND_MED,
    score_churn,
)


def test_healthy_account_is_low_risk() -> None:
    r = score_churn(spend_trend=20.0, open_rate=80.0, days_to_expiry=180)
    assert r.band == BAND_LOW
    assert r.score < 40


def test_collapsing_account_is_high_risk() -> None:
    r = score_churn(spend_trend=-80.0, open_rate=10.0, days_to_expiry=5)
    assert r.band == BAND_HIGH
    assert r.score >= 70
    assert any("spend down" in x for x in r.reasons)
    assert any("expires in" in x for x in r.reasons)


def test_expired_contract_adds_pressure() -> None:
    expired = score_churn(0, 50, days_to_expiry=-5)
    healthy_long = score_churn(0, 50, days_to_expiry=200)
    assert expired.score > healthy_long.score
    assert "contract expired" in expired.reasons


def test_no_contract_is_a_reason() -> None:
    r = score_churn(0, 50, days_to_expiry=None)
    assert "no active contract" in r.reasons


def test_clamps_inputs() -> None:
    # Extreme inputs must not crash or exceed 0..100.
    r = score_churn(spend_trend=-9999, open_rate=-50, days_to_expiry=-9999)
    assert 0 <= r.score <= 100
    assert r.band == BAND_HIGH


def test_band_boundaries() -> None:
    # Construct inputs to land in mid band.
    r = score_churn(spend_trend=-40, open_rate=40, days_to_expiry=45)
    assert r.band in (BAND_LOW, BAND_MED, BAND_HIGH)
    # Deterministic: same inputs → same output.
    r2 = score_churn(spend_trend=-40, open_rate=40, days_to_expiry=45)
    assert r == r2
