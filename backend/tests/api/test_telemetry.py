"""Telemetry endpoint tests: creation, retrieval, validation, 404s, and
that posting telemetry updates the owning asset's latest_telemetry.
"""


def _create_asset(client, name="Solar 1", asset_type="solar"):
    return client.post(
        "/api/v1/assets", json={"name": name, "type": asset_type, "capabilities": []}
    ).json()


def test_create_telemetry_for_existing_asset(client):
    asset = _create_asset(client)
    response = client.post(
        "/api/v1/telemetry",
        json={
            "asset_id": asset["id"],
            "timestamp": "2026-08-13T10:00:00+00:00",
            "power_kw": 5.5,
            "available": True,
            "operating_state": "online",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["asset_id"] == asset["id"]
    assert body["power_kw"] == 5.5


def test_create_telemetry_for_missing_asset_returns_404(client):
    response = client.post(
        "/api/v1/telemetry",
        json={
            "asset_id": "does-not-exist",
            "timestamp": "2026-08-13T10:00:00+00:00",
            "power_kw": 1.0,
            "available": True,
            "operating_state": "online",
        },
    )
    assert response.status_code == 404


def test_create_telemetry_invalid_soc_returns_422(client):
    asset = _create_asset(client)
    response = client.post(
        "/api/v1/telemetry",
        json={
            "asset_id": asset["id"],
            "timestamp": "2026-08-13T10:00:00+00:00",
            "power_kw": 1.0,
            "soc_percent": 150,
            "available": True,
            "operating_state": "online",
        },
    )
    assert response.status_code == 422


def test_list_telemetry_filtered_by_asset(client):
    solar = _create_asset(client, "Solar 1", "solar")
    battery = _create_asset(client, "Battery 1", "battery")

    for asset in (solar, battery):
        client.post(
            "/api/v1/telemetry",
            json={
                "asset_id": asset["id"],
                "timestamp": "2026-08-13T10:00:00+00:00",
                "power_kw": 2.0,
                "available": True,
                "operating_state": "online",
            },
        )

    response = client.get("/api/v1/telemetry", params={"asset_id": solar["id"]})
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["asset_id"] == solar["id"]

    assert len(client.get("/api/v1/telemetry").json()) == 2


def test_posting_telemetry_updates_asset_latest_telemetry(client):
    asset = _create_asset(client)
    client.post(
        "/api/v1/telemetry",
        json={
            "asset_id": asset["id"],
            "timestamp": "2026-08-13T09:00:00+00:00",
            "power_kw": 1.0,
            "available": True,
            "operating_state": "online",
        },
    )
    client.post(
        "/api/v1/telemetry",
        json={
            "asset_id": asset["id"],
            "timestamp": "2026-08-13T10:00:00+00:00",
            "power_kw": 3.0,
            "available": True,
            "operating_state": "online",
        },
    )

    response = client.get(f"/api/v1/assets/{asset['id']}")
    latest = response.json()["latest_telemetry"]
    assert latest is not None
    assert latest["power_kw"] == 3.0
