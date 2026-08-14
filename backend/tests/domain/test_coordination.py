from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.domain import (
    Allocation,
    AllocationAction,
    CoordinationRun,
    CoordinationRunStatus,
    Impact,
    Telemetry,
    TriggerReason,
)


class TestAllocation:
    def test_valid_creation_matches_spec_example(self):
        allocation = Allocation(
            coordination_run_id="run-1",
            asset_id="ev-1",
            action=AllocationAction.CHARGE,
            allocated_power_kw=3.5,
            reason=(
                "Charging is feasible while maintaining battery reserve and grid limit."
            ),
        )
        assert allocation.action is AllocationAction.CHARGE
        assert allocation.allocated_power_kw == 3.5

    def test_reason_required(self):
        with pytest.raises(ValidationError):
            Allocation(
                coordination_run_id="run-1",
                asset_id="ev-1",
                action=AllocationAction.DEFER,
            )

    def test_reason_must_not_be_blank(self):
        with pytest.raises(ValidationError):
            Allocation(
                coordination_run_id="run-1",
                asset_id="ev-1",
                action=AllocationAction.DEFER,
                reason="",
            )

    def test_invalid_action_rejected(self):
        with pytest.raises(ValidationError):
            Allocation(
                coordination_run_id="run-1",
                asset_id="ev-1",
                action="teleport",
                reason="x",
            )

    def test_allocated_power_must_be_non_negative(self):
        with pytest.raises(ValidationError):
            Allocation(
                coordination_run_id="run-1",
                asset_id="ev-1",
                action=AllocationAction.CHARGE,
                allocated_power_kw=-1.0,
                reason="x",
            )

    def test_hold_action_with_no_power(self):
        allocation = Allocation(
            coordination_run_id="run-1",
            asset_id="load-1",
            action=AllocationAction.HOLD,
            reason="No change needed this cycle.",
        )
        assert allocation.allocated_power_kw is None

    def test_optional_fields_default(self):
        allocation = Allocation(
            coordination_run_id="run-1", asset_id="load-1", action=AllocationAction.HOLD, reason="x"
        )
        assert allocation.source_intent_id is None
        assert allocation.constraints_considered == []
        assert allocation.feasible is True


class TestCoordinationRun:
    def test_valid_creation_minimal(self):
        run = CoordinationRun(trigger_reason=TriggerReason.SOLAR_SURPLUS)
        assert run.status is CoordinationRunStatus.PENDING
        assert run.allocations == []
        assert run.impact is None

    def test_trigger_reason_required(self):
        with pytest.raises(ValidationError):
            CoordinationRun()

    def test_invalid_trigger_reason_rejected(self):
        with pytest.raises(ValidationError):
            CoordinationRun(trigger_reason="because_i_felt_like_it")

    def test_invalid_status_rejected(self):
        with pytest.raises(ValidationError):
            CoordinationRun(trigger_reason=TriggerReason.PEAK_DEMAND, status="sleeping")

    # Representative examples for each MVP scenario trigger.

    def test_solar_surplus_scenario(self):
        run = CoordinationRun(trigger_reason=TriggerReason.SOLAR_SURPLUS)
        assert run.trigger_reason is TriggerReason.SOLAR_SURPLUS

    def test_peak_demand_scenario(self):
        run = CoordinationRun(
            trigger_reason=TriggerReason.PEAK_DEMAND,
            grid_snapshot=Telemetry(
                asset_id="grid-1",
                timestamp=datetime(2026, 8, 13, 18, 0, tzinfo=UTC),
                power_kw=48.0,
            ),
        )
        assert run.grid_snapshot.power_kw == 48.0

    def test_grid_outage_scenario(self):
        run = CoordinationRun(
            trigger_reason=TriggerReason.GRID_OUTAGE,
            grid_snapshot=Telemetry(
                asset_id="grid-1",
                timestamp=datetime(2026, 8, 13, 18, 0, tzinfo=UTC),
                power_kw=0.0,
                available=False,
            ),
        )
        assert run.grid_snapshot.available is False

    def test_full_run_with_allocations_and_impact(self):
        run = CoordinationRun(
            id="run-1",
            trigger_reason=TriggerReason.PEAK_DEMAND,
            status=CoordinationRunStatus.COMPLETED,
            allocations=[
                Allocation(
                    coordination_run_id="run-1",
                    asset_id="ev-1",
                    action=AllocationAction.DEFER,
                    reason="Deferred to protect battery reserve during peak demand.",
                ),
                Allocation(
                    coordination_run_id="run-1",
                    asset_id="battery-1",
                    action=AllocationAction.DISCHARGE,
                    allocated_power_kw=2.0,
                    reason="Discharging battery to offset peak grid import.",
                ),
            ],
            impact=Impact(coordination_run_id="run-1", peak_demand_reduction_kw=2.0),
        )
        assert len(run.allocations) == 2
        assert run.impact.peak_demand_reduction_kw == 2.0

    def test_serialization_roundtrip(self):
        run = CoordinationRun(
            id="run-1",
            trigger_reason=TriggerReason.SOLAR_SURPLUS,
            allocations=[
                Allocation(
                    coordination_run_id="run-1",
                    asset_id="battery-1",
                    action=AllocationAction.CHARGE,
                    allocated_power_kw=2.5,
                    reason="Absorbing solar surplus.",
                )
            ],
        )
        restored = CoordinationRun.model_validate(run.model_dump(mode="json"))
        assert restored == run
