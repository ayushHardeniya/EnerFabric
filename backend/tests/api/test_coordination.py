"""Coordination endpoint tests: the endpoint must assemble persisted
state and invoke the existing (unmodified) coordination engine, then
persist and return the resulting CoordinationRun.
"""


def _create_asset(client, name, asset_type, capabilities):
    response = client.post(
        "/api/v1/assets", json={"name": name, "type": asset_type, "capabilities": capabilities}
    )
    assert response.status_code == 201
    return response.json()


def _post_telemetry(client, asset_id, **overrides):
    payload = {
        "asset_id": asset_id,
        "timestamp": "2026-08-13T10:00:00+00:00",
        "power_kw": 0.0,
        "available": True,
        "operating_state": "online",
    }
    payload.update(overrides)
    response = client.post("/api/v1/telemetry", json=payload)
    assert response.status_code == 201


def _seed_ev_charging_scenario(client):
    solar = _create_asset(
        client, "Rooftop Solar", "solar", [{"type": "generate", "max_power_kw": 10.0}]
    )
    battery = _create_asset(
        client,
        "Site Battery",
        "battery",
        [
            {"type": "charge", "max_power_kw": 5.0, "capacity_kwh": 20.0},
            {"type": "discharge", "max_power_kw": 5.0, "capacity_kwh": 20.0},
        ],
    )
    ev = _create_asset(
        client,
        "EV Charger",
        "ev_charger",
        [{"type": "charge", "max_power_kw": 6.0, "capacity_kwh": 40.0}],
    )
    grid = _create_asset(client, "Grid Connection", "grid", [])

    _post_telemetry(client, solar["id"], power_kw=8.0)
    _post_telemetry(client, battery["id"], power_kw=0.0, soc_percent=50.0)
    _post_telemetry(client, ev["id"], power_kw=0.0, soc_percent=20.0)
    _post_telemetry(client, grid["id"], power_kw=0.0)

    intent_response = client.post(
        "/api/v1/intents",
        json={
            "type": "target_soc_by_deadline",
            "asset_id": ev["id"],
            "description": "Charge to 80% before 7am",
            "target_soc_percent": 80,
            "deadline": "2026-08-14T07:00:00+00:00",
        },
    )
    assert intent_response.status_code == 201

    return {"solar": solar, "battery": battery, "ev": ev, "grid": grid}


def test_coordination_run_invokes_engine_and_persists(client):
    assets = _seed_ev_charging_scenario(client)

    response = client.post("/api/v1/coordination/runs", json={"trigger_reason": "solar_surplus"})
    assert response.status_code == 201
    run = response.json()

    assert run["id"]
    assert run["status"] == "completed"
    assert run["trigger_reason"] == "solar_surplus"
    assert run["allocations"]

    ev_allocations = [a for a in run["allocations"] if a["asset_id"] == assets["ev"]["id"]]
    assert len(ev_allocations) == 1
    assert ev_allocations[0]["action"] == "charge"
    assert ev_allocations[0]["feasible"] is True
    assert ev_allocations[0]["reason"]

    for allocation in run["allocations"]:
        assert allocation["reason"]


def test_get_coordination_run_returns_persisted_run(client):
    _seed_ev_charging_scenario(client)
    created = client.post(
        "/api/v1/coordination/runs", json={"trigger_reason": "manual"}
    ).json()

    response = client.get(f"/api/v1/coordination/runs/{created['id']}")
    assert response.status_code == 200
    fetched = response.json()
    assert fetched["id"] == created["id"]
    assert fetched["allocations"] == created["allocations"]


def test_get_missing_coordination_run_returns_404(client):
    response = client.get("/api/v1/coordination/runs/does-not-exist")
    assert response.status_code == 404


def test_coordination_run_with_no_assets_is_empty_but_valid(client):
    response = client.post("/api/v1/coordination/runs", json={"trigger_reason": "manual"})
    assert response.status_code == 201
    run = response.json()
    assert run["allocations"] == []
    assert run["status"] == "completed"
