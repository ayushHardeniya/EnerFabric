"""Tests for the pure per-device-type step functions in
app/simulator/profiles.py — each covers one DER type's behaviour in
isolation from the ``DERSimulator`` orchestrator.
"""

from datetime import UTC, datetime

from app.domain import OperatingState
from app.simulator.devices import (
    BatteryConfig,
    CriticalLoadConfig,
    EVChargerConfig,
    FlexibleLoadConfig,
    GridConfig,
    SolarConfig,
)
from app.simulator.profiles import (
    step_battery,
    step_critical_load,
    step_ev_charger,
    step_flexible_load,
    step_grid,
    step_solar,
)
from app.simulator.state import DeviceState


def _at(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 8, 13, hour, minute, tzinfo=UTC)


class TestSolarProfile:
    def test_zero_before_sunrise(self):
        config = SolarConfig(asset_id="solar-1", sunrise_hour=6, sunset_hour=18)
        state = step_solar(config, _at(5))
        assert state.power_kw == 0.0
        assert state.operating_state == OperatingState.IDLE

    def test_zero_after_sunset(self):
        config = SolarConfig(asset_id="solar-1", sunrise_hour=6, sunset_hour=18)
        state = step_solar(config, _at(19))
        assert state.power_kw == 0.0

    def test_peaks_near_solar_noon(self):
        config = SolarConfig(asset_id="solar-1", max_power_kw=10.0, sunrise_hour=6, sunset_hour=18)
        state = step_solar(config, _at(12))
        assert state.power_kw == config.max_power_kw
        assert state.operating_state == OperatingState.ACTIVE

    def test_generation_never_exceeds_max_power(self):
        config = SolarConfig(asset_id="solar-1", max_power_kw=10.0, sunrise_hour=6, sunset_hour=18)
        for hour in range(0, 24):
            assert step_solar(config, _at(hour)).power_kw <= config.max_power_kw

    def test_deterministic_repeated_call(self):
        config = SolarConfig(asset_id="solar-1")
        assert step_solar(config, _at(10)) == step_solar(config, _at(10))


class TestBatteryProfile:
    def test_charges_during_charge_window(self):
        config = BatteryConfig(
            asset_id="battery-1", max_charge_kw=4.0, capacity_kwh=20.0, charge_window=(9, 15)
        )
        previous = DeviceState(soc_percent=50.0)
        state = step_battery(config, previous, _at(10), tick_hours=0.25)
        assert state.power_kw < 0
        assert state.soc_percent > 50.0
        assert state.operating_state == OperatingState.ACTIVE

    def test_discharges_during_discharge_window_above_reserve(self):
        config = BatteryConfig(
            asset_id="battery-1",
            max_discharge_kw=4.0,
            capacity_kwh=20.0,
            reserve_percent=10.0,
            discharge_window=(18, 22),
        )
        previous = DeviceState(soc_percent=50.0)
        state = step_battery(config, previous, _at(19), tick_hours=0.25)
        assert state.power_kw > 0
        assert state.soc_percent < 50.0

    def test_discharge_never_crosses_reserve_floor(self):
        config = BatteryConfig(
            asset_id="battery-1",
            max_discharge_kw=100.0,
            capacity_kwh=20.0,
            reserve_percent=10.0,
            discharge_window=(18, 22),
        )
        previous = DeviceState(soc_percent=12.0)
        state = step_battery(config, previous, _at(19), tick_hours=1.0)
        assert state.soc_percent >= config.reserve_percent

    def test_discharge_blocked_when_at_reserve_floor(self):
        config = BatteryConfig(
            asset_id="battery-1", reserve_percent=10.0, discharge_window=(18, 22)
        )
        previous = DeviceState(soc_percent=10.0)
        state = step_battery(config, previous, _at(19), tick_hours=0.25)
        assert state.power_kw == 0.0
        assert state.soc_percent == 10.0

    def test_charge_never_exceeds_full(self):
        config = BatteryConfig(
            asset_id="battery-1", max_charge_kw=100.0, capacity_kwh=20.0, charge_window=(9, 15)
        )
        previous = DeviceState(soc_percent=98.0)
        state = step_battery(config, previous, _at(10), tick_hours=1.0)
        assert state.soc_percent <= 100.0

    def test_charge_power_capped_by_capability_max(self):
        config = BatteryConfig(
            asset_id="battery-1", max_charge_kw=2.0, capacity_kwh=100.0, charge_window=(9, 15)
        )
        previous = DeviceState(soc_percent=10.0)
        state = step_battery(config, previous, _at(10), tick_hours=1.0)
        assert abs(state.power_kw) <= config.max_charge_kw

    def test_discharge_power_capped_by_capability_max(self):
        config = BatteryConfig(
            asset_id="battery-1",
            max_discharge_kw=2.0,
            capacity_kwh=100.0,
            reserve_percent=0.0,
            discharge_window=(18, 22),
        )
        previous = DeviceState(soc_percent=90.0)
        state = step_battery(config, previous, _at(19), tick_hours=1.0)
        assert state.power_kw <= config.max_discharge_kw

    def test_holds_outside_charge_and_discharge_windows(self):
        config = BatteryConfig(
            asset_id="battery-1", charge_window=(9, 15), discharge_window=(18, 22)
        )
        previous = DeviceState(soc_percent=50.0)
        state = step_battery(config, previous, _at(2), tick_hours=0.25)
        assert state.power_kw == 0.0
        assert state.soc_percent == 50.0
        assert state.operating_state == OperatingState.IDLE

    def test_falls_back_to_initial_soc_when_previous_has_none(self):
        config = BatteryConfig(asset_id="battery-1", initial_soc_percent=42.0)
        previous = DeviceState(soc_percent=None)
        state = step_battery(config, previous, _at(2), tick_hours=0.25)
        assert state.soc_percent == 42.0


class TestEvChargerProfile:
    def test_charges_when_below_full(self):
        config = EVChargerConfig(asset_id="ev-1", max_power_kw=7.0, capacity_kwh=60.0)
        previous = DeviceState(soc_percent=40.0)
        state = step_ev_charger(config, previous, _at(10), tick_hours=0.25)
        assert state.power_kw < 0
        assert state.soc_percent > 40.0
        assert state.operating_state == OperatingState.ACTIVE

    def test_holds_once_full(self):
        config = EVChargerConfig(asset_id="ev-1")
        previous = DeviceState(soc_percent=100.0)
        state = step_ev_charger(config, previous, _at(10), tick_hours=0.25)
        assert state.power_kw == 0.0
        assert state.soc_percent == 100.0
        assert state.operating_state == OperatingState.IDLE

    def test_soc_progression_reaches_full_without_overshoot(self):
        config = EVChargerConfig(asset_id="ev-1", max_power_kw=7.0, capacity_kwh=10.0)
        state = DeviceState(soc_percent=90.0)
        for _ in range(20):
            state = step_ev_charger(config, state, _at(10), tick_hours=0.25)
            assert 0.0 <= state.soc_percent <= 100.0
        assert state.soc_percent == 100.0


class TestFlexibleLoadProfile:
    def test_draws_full_power_within_active_window(self):
        config = FlexibleLoadConfig(asset_id="flex-1", max_power_kw=3.0, active_window=(9, 17))
        state = step_flexible_load(config, _at(12))
        assert state.power_kw == -3.0
        assert state.operating_state == OperatingState.ACTIVE

    def test_draws_nothing_outside_active_window(self):
        config = FlexibleLoadConfig(asset_id="flex-1", max_power_kw=3.0, active_window=(9, 17))
        state = step_flexible_load(config, _at(20))
        assert state.power_kw == 0.0
        assert state.operating_state == OperatingState.IDLE


class TestCriticalLoadProfile:
    def test_demand_is_never_zero(self):
        config = CriticalLoadConfig(asset_id="crit-1", base_power_kw=2.0, peak_power_kw=4.0)
        for hour in range(0, 24):
            assert step_critical_load(config, _at(hour)).power_kw < 0

    def test_draws_peak_power_within_peak_window(self):
        config = CriticalLoadConfig(
            asset_id="crit-1", base_power_kw=2.0, peak_power_kw=4.0, peak_window=(18, 22)
        )
        state = step_critical_load(config, _at(19))
        assert state.power_kw == -4.0

    def test_draws_base_power_outside_peak_window(self):
        config = CriticalLoadConfig(
            asset_id="crit-1", base_power_kw=2.0, peak_power_kw=4.0, peak_window=(18, 22)
        )
        state = step_critical_load(config, _at(10))
        assert state.power_kw == -2.0


class TestGridProfile:
    def test_imports_to_cover_site_deficit(self):
        config = GridConfig(asset_id="grid-1")
        state = step_grid(config, site_net_power_kw=-5.0)
        assert state.power_kw == 5.0
        assert state.operating_state == OperatingState.ACTIVE

    def test_exports_site_surplus(self):
        config = GridConfig(asset_id="grid-1")
        state = step_grid(config, site_net_power_kw=5.0)
        assert state.power_kw == -5.0

    def test_import_clipped_to_configured_limit(self):
        config = GridConfig(asset_id="grid-1", import_limit_kw=3.0)
        state = step_grid(config, site_net_power_kw=-10.0)
        assert state.power_kw == 3.0

    def test_export_clipped_to_configured_limit(self):
        config = GridConfig(asset_id="grid-1", export_limit_kw=2.0)
        state = step_grid(config, site_net_power_kw=10.0)
        assert state.power_kw == -2.0

    def test_balanced_site_produces_idle_grid(self):
        config = GridConfig(asset_id="grid-1")
        state = step_grid(config, site_net_power_kw=0.0)
        assert state.power_kw == 0.0
        assert state.operating_state == OperatingState.IDLE

    def test_unavailable_grid_contributes_nothing(self):
        config = GridConfig(asset_id="grid-1", available=False)
        state = step_grid(config, site_net_power_kw=-50.0)
        assert state.power_kw == 0.0
        assert state.available is False
        assert state.operating_state == OperatingState.OFFLINE
