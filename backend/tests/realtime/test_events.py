"""The realtime event envelope: ``{"type", "timestamp", "data"}``, where
``data`` is the relevant domain model's own JSON shape.
"""

from datetime import UTC, datetime

from app.domain import (
    Allocation,
    AllocationAction,
    CoordinationRun,
    CoordinationRunStatus,
    OperatingState,
    Telemetry,
    TriggerReason,
)
from app.realtime.events import coordination_completed_event, telemetry_updated_event


def _telemetry() -> Telemetry:
    return Telemetry(
        asset_id="solar-1",
        timestamp=datetime(2026, 8, 14, 12, 0, tzinfo=UTC),
        power_kw=3.5,
        available=True,
        operating_state=OperatingState.ACTIVE,
    )


def test_telemetry_updated_event_envelope() -> None:
    event = telemetry_updated_event(_telemetry())

    assert event["type"] == "telemetry.updated"
    assert event["timestamp"]  # ISO-8601 string, present
    assert event["data"]["asset_id"] == "solar-1"
    assert event["data"]["power_kw"] == 3.5


def test_coordination_completed_event_envelope() -> None:
    run = CoordinationRun(
        triggered_at=datetime(2026, 8, 14, 12, 0, tzinfo=UTC),
        trigger_reason=TriggerReason.MANUAL,
        status=CoordinationRunStatus.COMPLETED,
        allocations=[
            Allocation(
                coordination_run_id="run-1",
                asset_id="solar-1",
                action=AllocationAction.GENERATE,
                feasible=True,
                reason="solar generation dispatched",
            )
        ],
        summary="ok",
    )

    event = coordination_completed_event(run)

    assert event["type"] == "coordination.completed"
    assert event["timestamp"]
    assert event["data"]["status"] == "completed"
    assert len(event["data"]["allocations"]) == 1
    assert event["data"]["allocations"][0]["asset_id"] == "solar-1"
