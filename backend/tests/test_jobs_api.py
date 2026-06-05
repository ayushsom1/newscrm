def test_admin_can_trigger_job(client, admin_headers) -> None:
    # Use daily_renewal_reminders — not pre-triggered by the engine tests, so
    # the idempotency guard doesn't return an older row.
    r = client.post(
        "/jobs/daily_renewal_reminders/run", headers=admin_headers
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["job_name"] == "daily_renewal_reminders"
    assert body["status"] == "SUCCESS"
    assert body["triggered_by"].startswith("USER:")


def test_non_admin_cannot_trigger_job(client, accounts_headers) -> None:
    r = client.post(
        "/jobs/nightly_churn_recompute/run", headers=accounts_headers
    )
    assert r.status_code == 403


def test_unknown_job_returns_404(client, admin_headers) -> None:
    r = client.post("/jobs/not_a_real_job/run", headers=admin_headers)
    assert r.status_code == 404


def test_list_jobs_returns_known_names_and_last_run(client, admin_headers) -> None:
    # trigger so we have a last_run for at least one job
    client.post(
        "/jobs/daily_expire_contracts/run", headers=admin_headers
    )
    r = client.get("/jobs", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    names = [j["name"] for j in body["jobs"]]
    for n in (
        "nightly_churn_recompute",
        "daily_expire_contracts",
        "daily_renewal_reminders",
    ):
        assert n in names
    expired_job = next(
        j for j in body["jobs"] if j["name"] == "daily_expire_contracts"
    )
    assert expired_job["last_run"] is not None
