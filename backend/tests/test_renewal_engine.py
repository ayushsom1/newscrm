from app.engines.renewal import evaluate_renewal


def test_healthy_far_renewal_is_low() -> None:
    r = evaluate_renewal(days_to_renew=60, missed_payments=0)
    assert r.severity == "low"
    assert not r.at_risk
    assert r.reasons == []


def test_overdue_is_high() -> None:
    r = evaluate_renewal(days_to_renew=-3, missed_payments=0)
    assert r.severity == "high"
    assert r.at_risk
    assert any("overdue" in x for x in r.reasons)


def test_two_missed_payments_is_high() -> None:
    r = evaluate_renewal(days_to_renew=120, missed_payments=2)
    assert r.severity == "high"
    assert any("2 missed" in x for x in r.reasons)


def test_within_two_weeks_is_med() -> None:
    r = evaluate_renewal(days_to_renew=10, missed_payments=0)
    assert r.severity == "med"
    assert r.at_risk


def test_one_missed_payment_bumps_low_to_med() -> None:
    r = evaluate_renewal(days_to_renew=60, missed_payments=1)
    assert r.severity == "med"


def test_negative_missed_payments_treated_as_zero() -> None:
    r = evaluate_renewal(days_to_renew=60, missed_payments=-4)
    assert r.severity == "low"
