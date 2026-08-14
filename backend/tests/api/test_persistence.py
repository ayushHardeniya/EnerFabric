"""Explicit tests that data survives across separate database sessions —
not just within the session that wrote it. Each ``client`` request in
this test suite already opens and closes its own ``Session`` (see the
``get_db`` override in conftest.py), so any test using the API across
multiple requests exercises this; these tests do it directly at the
repository layer too, to make the guarantee unambiguous.
"""

from datetime import UTC, datetime

from app.db import repository as repo
from app.domain import Asset, AssetType, Telemetry


def test_asset_written_in_one_session_is_visible_in_another(session_factory):
    session_a = session_factory()
    try:
        created = repo.create_asset(session_a, Asset(name="Solar 1", type=AssetType.SOLAR))
    finally:
        session_a.close()

    session_b = session_factory()
    try:
        fetched = repo.get_asset(session_b, created.id)
    finally:
        session_b.close()

    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.name == "Solar 1"


def test_telemetry_written_in_one_session_visible_in_another(session_factory):
    session_a = session_factory()
    try:
        asset = repo.create_asset(session_a, Asset(name="Battery 1", type=AssetType.BATTERY))
        repo.create_telemetry(
            session_a,
            Telemetry(
                asset_id=asset.id,
                timestamp=datetime(2026, 8, 13, 10, 0, tzinfo=UTC),
                power_kw=2.5,
                soc_percent=60,
            ),
        )
    finally:
        session_a.close()

    session_b = session_factory()
    try:
        rows = repo.list_telemetry(session_b, asset_id=asset.id)
        refetched_asset = repo.get_asset(session_b, asset.id)
    finally:
        session_b.close()

    assert len(rows) == 1
    assert rows[0].power_kw == 2.5
    assert refetched_asset.latest_telemetry is not None
    assert refetched_asset.latest_telemetry.soc_percent == 60


def test_coordination_run_survives_across_client_requests(client):
    created = client.post("/api/v1/coordination/runs", json={"trigger_reason": "manual"}).json()

    # A fresh request opens and closes its own session (see conftest's
    # get_db override) — this GET cannot see the POST's in-memory state
    # unless the data actually made it to the database.
    refetched = client.get(f"/api/v1/coordination/runs/{created['id']}").json()
    assert refetched["id"] == created["id"]
