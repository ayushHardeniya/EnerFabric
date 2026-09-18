"""Asset endpoint tests: creation, retrieval, listing, validation, 404s."""


def test_create_asset_returns_201_with_generated_id(client):
    response = client.post(
        "/api/v1/assets",
        json={
            "name": "Rooftop Solar",
            "type": "solar",
            "capabilities": [{"type": "generate", "max_power_kw": 10.0}],
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["id"]
    assert body["name"] == "Rooftop Solar"
    assert body["type"] == "solar"
    assert body["capabilities"][0]["max_power_kw"] == 10.0
    assert body["latest_telemetry"] is None


def test_list_assets_empty_then_populated(client):
    assert client.get("/api/v1/assets").json() == []

    client.post("/api/v1/assets", json={"name": "Battery", "type": "battery", "capabilities": []})
    response = client.get("/api/v1/assets")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_asset_by_id(client):
    created = client.post(
        "/api/v1/assets", json={"name": "EV Charger", "type": "ev_charger", "capabilities": []}
    ).json()

    response = client.get(f"/api/v1/assets/{created['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_missing_asset_returns_404(client):
    response = client.get("/api/v1/assets/does-not-exist")
    assert response.status_code == 404


def test_create_asset_missing_required_field_returns_422(client):
    response = client.post("/api/v1/assets", json={"type": "solar"})
    assert response.status_code == 422


def test_create_asset_invalid_capability_bounds_returns_422(client):
    response = client.post(
        "/api/v1/assets",
        json={
            "name": "Bad Battery",
            "type": "battery",
            "capabilities": [{"type": "charge", "max_power_kw": 5.0, "min_power_kw": 10.0}],
        },
    )
    assert response.status_code == 422


def test_create_asset_duplicate_capability_type_returns_422(client):
    response = client.post(
        "/api/v1/assets",
        json={
            "name": "Weird Battery",
            "type": "battery",
            "capabilities": [
                {"type": "charge", "max_power_kw": 5.0},
                {"type": "charge", "max_power_kw": 3.0},
            ],
        },
    )
    assert response.status_code == 422
