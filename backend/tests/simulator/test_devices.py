"""Validation and Capability-shape tests for the simulator's static
``*Config`` dataclasses (app/simulator/devices.py).
"""

import pytest

from app.domain import CapabilityType
from app.simulator.devices import (
    BatteryConfig,
    CriticalLoadConfig,
    EVChargerConfig,
    FlexibleLoadConfig,
    GridConfig,
    SolarConfig,
)


class TestSolarConfig:
    def test_valid_config_capabilities(self):
        config = SolarConfig(asset_id="solar-1", max_power_kw=8.0)
        (capability,) = config.capabilities()
        assert capability.type == CapabilityType.GENERATE
        assert capability.max_power_kw == 8.0

    def test_rejects_non_positive_max_power(self):
        with pytest.raises(ValueError, match="max_power_kw"):
            SolarConfig(asset_id="solar-1", max_power_kw=0)

    def test_rejects_sunrise_after_sunset(self):
        with pytest.raises(ValueError, match="sunrise_hour"):
            SolarConfig(asset_id="solar-1", sunrise_hour=19, sunset_hour=6)


class TestBatteryConfig:
    def test_valid_config_capabilities(self):
        config = BatteryConfig(asset_id="battery-1", max_charge_kw=4.0, max_discharge_kw=6.0)
        types = {c.type for c in config.capabilities()}
        assert types == {CapabilityType.CHARGE, CapabilityType.DISCHARGE}

    def test_rejects_non_positive_capacity(self):
        with pytest.raises(ValueError, match="capacity_kwh"):
            BatteryConfig(asset_id="battery-1", capacity_kwh=0)

    def test_rejects_out_of_range_reserve_percent(self):
        with pytest.raises(ValueError, match="reserve_percent"):
            BatteryConfig(asset_id="battery-1", reserve_percent=150)

    def test_rejects_out_of_range_initial_soc(self):
        with pytest.raises(ValueError, match="initial_soc_percent"):
            BatteryConfig(asset_id="battery-1", initial_soc_percent=-1)

    def test_rejects_inverted_charge_window(self):
        with pytest.raises(ValueError, match="charge_window"):
            BatteryConfig(asset_id="battery-1", charge_window=(15, 9))


class TestEVChargerConfig:
    def test_valid_config_capabilities(self):
        config = EVChargerConfig(asset_id="ev-1", max_power_kw=7.0)
        (capability,) = config.capabilities()
        assert capability.type == CapabilityType.CHARGE
        assert capability.max_power_kw == 7.0

    def test_rejects_non_positive_max_power(self):
        with pytest.raises(ValueError, match="max_power_kw"):
            EVChargerConfig(asset_id="ev-1", max_power_kw=0)

    def test_rejects_out_of_range_initial_soc(self):
        with pytest.raises(ValueError, match="initial_soc_percent"):
            EVChargerConfig(asset_id="ev-1", initial_soc_percent=101)


class TestFlexibleLoadConfig:
    def test_valid_config_capabilities(self):
        config = FlexibleLoadConfig(asset_id="flex-1", max_power_kw=3.0)
        (capability,) = config.capabilities()
        assert capability.type == CapabilityType.CONSUME
        assert capability.max_power_kw == 3.0

    def test_rejects_inverted_active_window(self):
        with pytest.raises(ValueError, match="active_window"):
            FlexibleLoadConfig(asset_id="flex-1", active_window=(17, 9))


class TestCriticalLoadConfig:
    def test_valid_config_capabilities(self):
        config = CriticalLoadConfig(asset_id="crit-1", base_power_kw=2.0, peak_power_kw=5.0)
        (capability,) = config.capabilities()
        assert capability.type == CapabilityType.CONSUME
        assert capability.max_power_kw == 5.0

    def test_rejects_peak_below_base(self):
        with pytest.raises(ValueError, match="peak_power_kw"):
            CriticalLoadConfig(asset_id="crit-1", base_power_kw=5.0, peak_power_kw=2.0)


class TestGridConfig:
    def test_valid_config_has_no_capabilities(self):
        config = GridConfig(asset_id="grid-1")
        assert config.capabilities() == []

    def test_rejects_negative_import_limit(self):
        with pytest.raises(ValueError, match="import_limit_kw"):
            GridConfig(asset_id="grid-1", import_limit_kw=-1)

    def test_rejects_negative_export_limit(self):
        with pytest.raises(ValueError, match="export_limit_kw"):
            GridConfig(asset_id="grid-1", export_limit_kw=-1)
