"""WebSocket endpoint tests, against the real FastAPI app and its real
lifespan (see ``conftest.py`` — this is what binds ``ConnectionManager``'s
event loop exactly as it is bound in production), not a bare ASGI stub.

Covers: a connection can be established, a broadcast reaches a connected
client, a client is unregistered on disconnect, neither an abrupt
disconnect nor an unexpected (non-text) frame crashes the backend or
leaves ``/health``/the REST API unhealthy, and — the real end-to-end path
— a coordination run triggered over REST results in a
``coordination.completed`` event delivered to a connected client.
"""

import queue
import threading
import time

import pytest
from fastapi.testclient import TestClient

from app.realtime import manager


@pytest.fixture(autouse=True)
def _clear_connections():
    manager._connections.clear()
    yield
    manager._connections.clear()


def _wait_until_no_connections(timeout: float = 1.0) -> None:
    deadline = time.monotonic() + timeout
    while manager._connections and time.monotonic() < deadline:
        time.sleep(0.02)


def _receive_json_with_timeout(websocket, timeout: float = 5.0) -> dict:
    """``WebSocketTestSession.receive_json`` blocks with no timeout of its
    own; wrapping it in a background thread with a bounded ``queue.get``
    turns "the broadcast never arrived" into a clean test failure instead
    of an indefinitely hanging test run.
    """
    outcome: queue.Queue = queue.Queue()

    def _run() -> None:
        try:
            outcome.put(("ok", websocket.receive_json()))
        except Exception as exc:  # pragma: no cover - failure path only
            outcome.put(("error", exc))

    threading.Thread(target=_run, daemon=True).start()
    try:
        status, value = outcome.get(timeout=timeout)
    except queue.Empty:
        pytest.fail(f"no websocket message received within {timeout}s")
    if status == "error":
        raise value
    return value


def test_websocket_connection_can_be_established(client: TestClient) -> None:
    with client.websocket_connect("/api/v1/ws") as websocket:
        assert websocket is not None
        assert len(manager._connections) == 1


def test_a_broadcast_event_reaches_a_connected_client(client: TestClient) -> None:
    with client.websocket_connect("/api/v1/ws") as websocket:
        message = {
            "type": "telemetry.updated",
            "timestamp": "2026-08-14T12:00:00+00:00",
            "data": {"asset_id": "solar-1", "power_kw": 3.5},
        }

        manager.broadcast_threadsafe(message)

        assert _receive_json_with_timeout(websocket) == message


def test_client_is_unregistered_after_a_clean_disconnect(client: TestClient) -> None:
    with client.websocket_connect("/api/v1/ws"):
        assert len(manager._connections) == 1
    _wait_until_no_connections()
    assert len(manager._connections) == 0
    assert client.get("/health").status_code == 200


def test_an_unexpected_binary_frame_does_not_crash_the_backend(client: TestClient) -> None:
    with client.websocket_connect("/api/v1/ws") as websocket:
        websocket.send_bytes(b"\x00\x01not-the-expected-text-frame")
    _wait_until_no_connections()
    assert client.get("/health").status_code == 200


def test_the_backend_stays_healthy_across_repeated_connect_disconnect_cycles(
    client: TestClient,
) -> None:
    for _ in range(3):
        with client.websocket_connect("/api/v1/ws"):
            pass
    _wait_until_no_connections()
    assert manager._connections == set()
    assert client.get("/health").status_code == 200


def test_rest_api_is_unaffected_by_the_websocket_layer(client: TestClient) -> None:
    response = client.get("/api/v1/assets")
    assert response.status_code == 200
    assert response.json() == []


def test_coordination_run_over_rest_broadcasts_a_completed_event_to_websocket_clients(
    client: TestClient,
) -> None:
    """The real hook required by Milestone 6: POSTing a coordination run
    (the existing, unmodified REST endpoint/engine) must result in a
    ``coordination.completed`` WebSocket event for an already-connected
    client — proving the broadcast fires from the sync route handler's
    threadpool thread onto the bound asyncio loop, not just from a
    directly-invoked ``broadcast_threadsafe`` call.
    """
    with client.websocket_connect("/api/v1/ws") as websocket:
        response = client.post(
            "/api/v1/coordination/runs", json={"trigger_reason": "manual"}
        )
        assert response.status_code == 201
        run = response.json()

        event = _receive_json_with_timeout(websocket)

        assert event["type"] == "coordination.completed"
        assert event["data"]["id"] == run["id"]
        assert event["data"]["status"] == "completed"
