"""Integration-boundary tests: MQTT -> ``persist_telemetry`` -> the real
repository/DB layer, against an isolated SQLite database (see
``conftest.py``). ``app.mqtt.service.SessionLocal`` is monkeypatched to
point at the test database instead of the real (Postgres) engine, since
``persist_telemetry`` opens its own session rather than accepting one as
an argument (mirroring a real MQTT message handler, which has no request
to inject a session from).
"""

from datetime import UTC, datetime

from app.db import repository as repo
from app.domain import Asset, AssetType, OperatingState, Telemetry
from app.mqtt import service
from app.realtime import manager


def test_persist_telemetry_for_known_asset(monkeypatch, session_factory) -> None:
    monkeypatch.setattr(service, "SessionLocal", session_factory)

    setup_db = session_factory()
    repo.create_asset(setup_db, Asset(id="solar-1", name="Rooftop Solar", type=AssetType.SOLAR))
    setup_db.close()

    telemetry = Telemetry(
        asset_id="solar-1",
        timestamp=datetime(2026, 8, 13, 12, 0, tzinfo=UTC),
        power_kw=3.5,
        available=True,
        operating_state=OperatingState.ACTIVE,
    )
    service.persist_telemetry(telemetry)

    check_db = session_factory()
    stored = repo.list_telemetry(check_db, asset_id="solar-1")
    check_db.close()
    assert len(stored) == 1
    assert stored[0].power_kw == 3.5


def test_persist_telemetry_for_unknown_asset_is_discarded(monkeypatch, session_factory) -> None:
    monkeypatch.setattr(service, "SessionLocal", session_factory)

    telemetry = Telemetry(
        asset_id="does-not-exist",
        timestamp=datetime(2026, 8, 13, 12, 0, tzinfo=UTC),
        power_kw=1.0,
        available=True,
        operating_state=OperatingState.ONLINE,
    )
    service.persist_telemetry(telemetry)  # must not raise

    check_db = session_factory()
    stored = repo.list_telemetry(check_db, asset_id="does-not-exist")
    check_db.close()
    assert stored == []


def test_persist_telemetry_for_known_asset_broadcasts_a_websocket_event(
    monkeypatch, session_factory
) -> None:
    """Milestone 6's MQTT->WebSocket hook: a telemetry reading that is
    actually persisted must also be broadcast to realtime clients. No live
    broker or connected client is needed to prove this wiring — just that
    ``persist_telemetry`` calls ``ConnectionManager.broadcast_threadsafe``
    with the right event once persistence has succeeded.
    """
    monkeypatch.setattr(service, "SessionLocal", session_factory)
    broadcasts: list[dict] = []
    monkeypatch.setattr(manager, "broadcast_threadsafe", broadcasts.append)

    setup_db = session_factory()
    repo.create_asset(setup_db, Asset(id="solar-1", name="Rooftop Solar", type=AssetType.SOLAR))
    setup_db.close()

    telemetry = Telemetry(
        asset_id="solar-1",
        timestamp=datetime(2026, 8, 13, 12, 0, tzinfo=UTC),
        power_kw=3.5,
        available=True,
        operating_state=OperatingState.ACTIVE,
    )
    service.persist_telemetry(telemetry)

    assert len(broadcasts) == 1
    assert broadcasts[0]["type"] == "telemetry.updated"
    assert broadcasts[0]["data"]["asset_id"] == "solar-1"
    assert broadcasts[0]["data"]["power_kw"] == 3.5


def test_persist_telemetry_for_unknown_asset_does_not_broadcast(
    monkeypatch, session_factory
) -> None:
    monkeypatch.setattr(service, "SessionLocal", session_factory)
    broadcasts: list[dict] = []
    monkeypatch.setattr(manager, "broadcast_threadsafe", broadcasts.append)

    telemetry = Telemetry(
        asset_id="does-not-exist",
        timestamp=datetime(2026, 8, 13, 12, 0, tzinfo=UTC),
        power_kw=1.0,
        available=True,
        operating_state=OperatingState.ONLINE,
    )
    service.persist_telemetry(telemetry)

    assert broadcasts == []


def test_build_telemetry_subscriber_uses_settings() -> None:
    subscriber = service.build_telemetry_subscriber()
    assert subscriber._host  # constructed without connecting
    assert subscriber._on_telemetry is service.persist_telemetry
