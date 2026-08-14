"""Tests for DERSimulator: the orchestrator that advances a fleet of
device configs through simulated time and adapts the result into
domain-compatible Asset/Telemetry objects.
"""

from datetime import UTC, datetime

import pytest

from app.coordination import CoordinationContext, run_coordination
from app.domain import AssetType, CoordinationRunStatus, OperatingState
from app.simulator import (
    BatteryConfig,
    CriticalLoadConfig,
    DERSimulator,
    EVChargerConfig,
    FlexibleLoadConfig,
    GridConfig,
    SolarConfig,
    default_fleet,
)

START = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)


class TestInitialState:
    def test_seeds_stateful_devices_at_configured_initial_soc(self):
        simulator = DERSimulator(
            configs=(
                BatteryConfig(asset_id="battery-1", initial_soc_percent=55.0),
                EVChargerConfig(asset_id="ev-1", initial_soc_percent=33.0),
            )
        )
        state = simulator.initial_state(START)
        assert state.devices["battery-1"].soc_percent == 55.0
        assert state.devices["ev-1"].soc_percent == 33.0
        assert state.step == 0
        assert state.timestamp == START

    def test_stateless_devices_reflect_schedule_at_start_time(self):
        simulator = default_fleet()
        state = simulator.initial_state(START)
        assert state.devices["solar-1"].power_kw > 0


class TestStepDeterminism:
    def test_same_state_produces_same_next_state(self):
        simulator = default_fleet()
        state = simulator.initial_state(START)
        next_a = simulator.step(state)
        next_b = simulator.step(state)
        assert next_a == next_b

    def test_repeated_full_run_is_reproducible(self):
        simulator = default_fleet()

        def run():
            state = simulator.initial_state(START)
            for _ in range(50):
                state = simulator.step(state)
            return state

        assert run() == run()

    def test_step_advances_timestamp_and_step_index(self):
        simulator = default_fleet(tick_minutes=15.0)
        state = simulator.initial_state(START)
        next_state = simulator.step(state)
        assert next_state.timestamp == START.replace(minute=15)
        assert next_state.step == state.step + 1


class TestTelemetryGeneration:
    def test_produces_one_telemetry_per_configured_device(self):
        simulator = default_fleet()
        state = simulator.initial_state(START)
        telemetry = simulator.telemetry(state)
        assert {t.asset_id for t in telemetry} == {
            "solar-1",
            "battery-1",
            "ev-1",
            "flex-1",
            "crit-1",
            "grid-1",
        }

    def test_telemetry_timestamp_matches_state(self):
        simulator = default_fleet()
        state = simulator.initial_state(START)
        telemetry = simulator.telemetry(state)
        assert all(t.timestamp == state.timestamp for t in telemetry)

    def test_telemetry_soc_within_domain_bounds_across_many_steps(self):
        simulator = default_fleet(tick_minutes=15.0)
        state = simulator.initial_state(START)
        for _ in range(200):
            state = simulator.step(state)
            for t in simulator.telemetry(state):
                if t.soc_percent is not None:
                    assert 0.0 <= t.soc_percent <= 100.0


class TestAssetConversion:
    def test_produces_one_asset_per_configured_device_with_matching_type(self):
        simulator = default_fleet()
        state = simulator.initial_state(START)
        assets = simulator.assets(state)
        by_id = {a.id: a for a in assets}
        assert by_id["solar-1"].type == AssetType.SOLAR
        assert by_id["battery-1"].type == AssetType.BATTERY
        assert by_id["ev-1"].type == AssetType.EV_CHARGER
        assert by_id["flex-1"].type == AssetType.FLEXIBLE_LOAD
        assert by_id["crit-1"].type == AssetType.CRITICAL_LOAD
        assert by_id["grid-1"].type == AssetType.GRID

    def test_asset_latest_telemetry_matches_state(self):
        simulator = default_fleet()
        state = simulator.initial_state(START)
        assets = simulator.assets(state)
        battery = next(a for a in assets if a.id == "battery-1")
        assert battery.latest_telemetry is not None
        assert battery.latest_telemetry.soc_percent == state.devices["battery-1"].soc_percent


class TestGridDerivation:
    def test_grid_imports_to_cover_deficit_from_other_devices(self):
        simulator = DERSimulator(
            configs=(
                CriticalLoadConfig(asset_id="crit-1", base_power_kw=5.0, peak_power_kw=5.0),
                GridConfig(asset_id="grid-1"),
            )
        )
        state = simulator.initial_state(START)
        assert state.devices["grid-1"].power_kw == pytest.approx(5.0)

    def test_grid_exports_site_surplus(self):
        simulator = DERSimulator(
            configs=(
                SolarConfig(asset_id="solar-1", max_power_kw=10.0, sunrise_hour=0, sunset_hour=24),
                GridConfig(asset_id="grid-1"),
            )
        )
        state = simulator.initial_state(datetime(2026, 8, 13, 12, 0, tzinfo=UTC))
        assert state.devices["grid-1"].power_kw < 0

    def test_grid_outage_reports_unavailable_regardless_of_demand(self):
        simulator = DERSimulator(
            configs=(
                CriticalLoadConfig(asset_id="crit-1", base_power_kw=5.0, peak_power_kw=5.0),
                GridConfig(asset_id="grid-1", available=False),
            )
        )
        state = simulator.initial_state(START)
        grid_state = state.devices["grid-1"]
        assert grid_state.power_kw == 0.0
        assert grid_state.available is False
        assert grid_state.operating_state == OperatingState.OFFLINE


class TestInvalidStates:
    def test_rejects_duplicate_asset_ids(self):
        with pytest.raises(ValueError, match="unique"):
            DERSimulator(
                configs=(
                    SolarConfig(asset_id="dup"),
                    FlexibleLoadConfig(asset_id="dup"),
                )
            )

    def test_rejects_more_than_one_grid(self):
        with pytest.raises(ValueError, match="GridConfig"):
            DERSimulator(configs=(GridConfig(asset_id="grid-1"), GridConfig(asset_id="grid-2")))

    def test_rejects_non_positive_tick_minutes(self):
        with pytest.raises(ValueError, match="tick_minutes"):
            DERSimulator(configs=(SolarConfig(asset_id="solar-1"),), tick_minutes=0)


class TestCoordinationEngineCompatibility:
    def test_simulated_fleet_can_be_run_through_the_coordination_engine(self):
        simulator = default_fleet()
        state = simulator.initial_state(datetime(2026, 8, 13, 12, 0, tzinfo=UTC))
        context = CoordinationContext(assets=simulator.assets(state), now=state.timestamp)
        run = run_coordination(context)
        assert run.status == CoordinationRunStatus.COMPLETED
        assert len(run.allocations) == len(simulator.configs)
