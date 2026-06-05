from app.engines.triage import is_sensitive, triage_engine


def test_non_delivery_is_auto() -> None:
    r = triage_engine("Paper not delivered today in Patan, please send replacement.")
    assert r.auto is True
    assert "delivery" in r.resolution.lower() or "hawker" in r.resolution.lower()


def test_pause_request_is_auto() -> None:
    r = triage_engine("Please pause my subscription for the next two weeks.")
    assert r.auto is True
    assert "paused" in r.resolution.lower()


def test_address_change_is_auto() -> None:
    r = triage_engine("I have moved to a new address, please update.")
    assert r.auto is True


def test_billing_dispute_always_escalates() -> None:
    r = triage_engine("You charged me twice this month, this is a billing dispute.")
    assert r.auto is False
    assert r.reason == "sensitive_keyword"


def test_legal_threats_escalate() -> None:
    r = triage_engine("If this is not refunded I will go to court.")
    assert r.auto is False


def test_abusive_complaint_escalates() -> None:
    r = triage_engine("The hawker was extremely rude and abusive to my family.")
    assert r.auto is False


def test_unknown_pattern_defaults_to_escalate() -> None:
    r = triage_engine("Random feedback about printing quality and ink.")
    # not in routine list, not in sensitive list -> escalate by default
    assert r.auto is False
    assert r.reason == "no_match"


def test_is_sensitive_is_case_insensitive() -> None:
    assert is_sensitive("REFUND REQUESTED IMMEDIATELY")
    assert not is_sensitive("missed paper today")
