"""Policy endpoint tests: creation, retrieval, validation."""


def test_create_and_list_policy(client):
    assert client.get("/api/v1/policies").json() == []

    response = client.post(
        "/api/v1/policies",
        json={
            "type": "limit_grid_import",
            "description": "Cap grid import at 50 kW",
            "threshold_kw": 50,
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["id"]
    assert body["enabled"] is True
    assert body["threshold_kw"] == 50

    listed = client.get("/api/v1/policies").json()
    assert len(listed) == 1
    assert listed[0]["id"] == body["id"]


def test_create_policy_invalid_threshold_percent_returns_422(client):
    response = client.post(
        "/api/v1/policies",
        json={
            "type": "maintain_battery_reserve",
            "description": "Bad reserve",
            "threshold_percent": 150,
        },
    )
    assert response.status_code == 422


def test_create_policy_missing_type_returns_422(client):
    response = client.post("/api/v1/policies", json={"description": "No type"})
    assert response.status_code == 422
