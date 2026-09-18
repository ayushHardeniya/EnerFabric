"""``ConnectionManager`` unit tests, against fake WebSocket-like objects
(no real network/ASGI connection needed) — connect/disconnect bookkeeping,
broadcasting to multiple clients, dropping an unresponsive client without
raising, and the thread-safe scheduling path ``app.mqtt.service`` and the
coordination route use to broadcast from outside the asyncio loop.
"""

import asyncio

import pytest

from app.realtime.manager import ConnectionManager


class _FakeWebSocket:
    def __init__(self, fail: bool = False) -> None:
        self.accepted = False
        self.sent: list[dict] = []
        self._fail = fail

    async def accept(self) -> None:
        self.accepted = True

    async def send_json(self, message: dict) -> None:
        if self._fail:
            raise RuntimeError("client connection is gone")
        self.sent.append(message)


@pytest.mark.asyncio
async def test_connect_accepts_and_registers_the_client() -> None:
    manager = ConnectionManager()
    ws = _FakeWebSocket()

    await manager.connect(ws)

    assert ws.accepted
    assert ws in manager._connections


def test_disconnect_removes_the_client() -> None:
    manager = ConnectionManager()
    ws = _FakeWebSocket()
    manager._connections.add(ws)

    manager.disconnect(ws)

    assert ws not in manager._connections


def test_disconnect_of_unknown_client_does_not_raise() -> None:
    manager = ConnectionManager()
    manager.disconnect(_FakeWebSocket())  # never connected


@pytest.mark.asyncio
async def test_broadcast_sends_the_message_to_every_connected_client() -> None:
    manager = ConnectionManager()
    ws1, ws2 = _FakeWebSocket(), _FakeWebSocket()
    await manager.connect(ws1)
    await manager.connect(ws2)
    message = {"type": "telemetry.updated", "data": {"asset_id": "solar-1"}}

    await manager.broadcast(message)

    assert ws1.sent == [message]
    assert ws2.sent == [message]


@pytest.mark.asyncio
async def test_broadcast_with_no_connected_clients_does_nothing() -> None:
    manager = ConnectionManager()
    await manager.broadcast({"type": "telemetry.updated", "data": {}})  # must not raise


@pytest.mark.asyncio
async def test_broadcast_drops_an_unresponsive_client_without_raising() -> None:
    manager = ConnectionManager()
    good, bad = _FakeWebSocket(), _FakeWebSocket(fail=True)
    await manager.connect(good)
    await manager.connect(bad)

    await manager.broadcast({"type": "telemetry.updated", "data": {}})

    assert good.sent
    assert bad not in manager._connections


def test_broadcast_threadsafe_before_loop_is_bound_is_a_noop() -> None:
    manager = ConnectionManager()
    # Simulates a broadcast attempted before the app's lifespan has
    # started (e.g. a stray call during startup) — must not raise.
    manager.broadcast_threadsafe({"type": "telemetry.updated", "data": {}})


def test_broadcast_threadsafe_schedules_delivery_onto_the_bound_loop() -> None:
    """Mirrors how ``app.mqtt.service.persist_telemetry`` calls this from
    paho-mqtt's background thread, and how the coordination route calls it
    from FastAPI's sync-handler threadpool: neither runs on the asyncio
    loop itself, so delivery must be scheduled onto it, not awaited
    directly.
    """
    manager = ConnectionManager()
    ws = _FakeWebSocket()
    message = {"type": "coordination.completed", "data": {"id": "run-1"}}

    async def scenario() -> None:
        await manager.connect(ws)
        manager.bind_loop(asyncio.get_running_loop())
        await asyncio.to_thread(manager.broadcast_threadsafe, message)
        await asyncio.sleep(0.05)  # let the scheduled coroutine actually run

    asyncio.run(scenario())

    assert ws.sent == [message]
