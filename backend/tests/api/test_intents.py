"""Intent endpoint tests: discriminated-union creation, retrieval,
validation, and 404s.
"""


def _create_asset(client, name="EV 1", asset_type="ev_charger"):
    return client.post(
        "/api/v1/assets", json={"name": name, "type": asset_type, "capabilities": []}
    ).json()


def test_create_target_soc_by_deadline_intent(client):
    asset = _create_asset(client)
    response = client.post(
        "/api/v1/intents",
        json={
            "type": "target_soc_by_deadline",
            "asset_id": asset["id"],
            "description": "Charge to 80% before 7am",
            "target_soc_percent": 80,
            "deadline": "2026-08-14T07:00:00+00:00",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["id"]
    assert body["type"] == "target_soc_by_deadline"
    assert body["target_soc_percent"] == 80


def test_create_minimum_reserve_intent(client):
    battery = _create_asset(client, "Battery 1", "battery")
    response = client.post(
        "/api/v1/intents",
        json={
            "type": "minimum_reserve",
            "asset_id": battery["id"],
            "description": "Maintain 30% reserve",
            "min_soc_percent": 30,
        },
    )
    assert response.status_code == 201
    assert response.json()["min_soc_percent"] == 30


def test_create_intent_for_missing_asset_returns_404(client):
    response = client.post(
        "/api/v1/intents",
        json={
            "type": "minimum_reserve",
            "asset_id": "does-not-exist",
            "description": "Maintain reserve",
            "min_soc_percent": 30,
        },
    )
    assert response.status_code == 404


def test_create_intent_missing_type_specific_field_returns_422(client):
    asset = _create_asset(client)
    response = client.post(
        "/api/v1/intents",
        json={
            "type": "target_soc_by_deadline",
            "asset_id": asset["id"],
            "description": "Missing deadline",
            "target_soc_percent": 80,
        },
    )
    assert response.status_code == 422


def test_create_deferrable_intent_invalid_window_returns_422(client):
    load = _create_asset(client, "Flexible Load 1", "flexible_load")
    response = client.post(
        "/api/v1/intents",
        json={
            "type": "deferrable",
            "asset_id": load["id"],
            "description": "Run overnight",
            "window_start": "2026-08-13T20:00:00+00:00",
            "window_end": "2026-08-13T18:00:00+00:00",
        },
    )
    assert response.status_code == 422


def test_list_intents_filtered_by_asset(client):
    asset_a = _create_asset(client, "EV A", "ev_charger")
    asset_b = _create_asset(client, "EV B", "ev_charger")
    for asset in (asset_a, asset_b):
        client.post(
            "/api/v1/intents",
            json={
                "type": "target_soc_by_deadline",
                "asset_id": asset["id"],
                "description": "Charge",
                "target_soc_percent": 80,
                "deadline": "2026-08-14T07:00:00+00:00",
            },
        )

    response = client.get("/api/v1/intents", params={"asset_id": asset_a["id"]})
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["asset_id"] == asset_a["id"]

    assert len(client.get("/api/v1/intents").json()) == 2
