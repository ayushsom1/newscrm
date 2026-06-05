from app.engines.printrun import forecast_print_run


def test_basic_forecast_no_returns_no_buffer() -> None:
    r = forecast_print_run(active_subs=1000)
    assert r.target == 1000


def test_returns_increase_target() -> None:
    r = forecast_print_run(active_subs=1000, newsstand_buffer=0, returns_pct=5)
    assert r.target == 1050


def test_buffer_added_before_returns_factor() -> None:
    r = forecast_print_run(active_subs=1000, newsstand_buffer=100, returns_pct=10)
    # (1000 + 100) * 1.10 = 1210
    assert r.target == 1210


def test_negative_inputs_clamped() -> None:
    r = forecast_print_run(active_subs=-50, newsstand_buffer=-10, returns_pct=-5)
    assert r.target == 0
    assert r.returns_pct == 0


def test_returns_pct_capped() -> None:
    r = forecast_print_run(active_subs=100, returns_pct=200)
    # 100 * (1 + 100/100) = 200
    assert r.target == 200
