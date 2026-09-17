from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.domain import Asset, AssetType, Capability, CapabilityType, Telemetry


def _telemetry(asset_id: str, **overrides) -> Telemetry:
    defaults = dict(
        asset_id=asset_id,
        timestamp=datetime(2026, 8, 13, 12, 0, tzinfo=UTC),
        power_kw=0.0,
    )
    defaults.update(overrides)
    return Telemetry(**defaults)


class TestCapability:
    def test_valid_creation(self):
        cap = Capability(type=CapabilityType.CHARGE, max_power_kw=7.0, min_power_kw=0)
        assert cap.max_power_kw == 7.0

    def test_min_greater_than_max_rejected(self):
        with pytest.raises(ValidationError):
            Capability(type=CapabilityType.CHARGE, max_power_kw=1.0, min_power_kw=5.0)

    def test_max_power_must_be_positive(self):
        with pytest.raises(ValidationError):
            Capability(type=CapabilityType.CHARGE, max_power_kw=0)

    def test_invalid_capability_type_rejected(self):
        with pytest.raises(ValidationError):
            Capability(type="teleport", max_power_kw=1.0)

    def test_capacity_kwh_optional(self):
        cap = Capability(type=CapabilityType.GENERATE, max_power_kw=5.0)
        assert cap.capacity_kwh is None


class TestAsset:
    def test_required_fields(self):
        with pytest.raises(ValidationError):
            Asset(type=AssetType.SOLAR)  # missing name

    def test_invalid_asset_type_rejected(self):
        with pytest.raises(ValidationError):
            Asset(name="Rooftop Array", type="nuclear_reactor")

    def test_id_defaults_when_omitted(self):
        a1 = Asset(name="A", type=AssetType.SOLAR)
        a2 = Asset(name="B", type=AssetType.SOLAR)
        assert a1.id and a2.id and a1.id != a2.id

    def test_duplicate_capability_type_rejected(self):
        with pytest.raises(ValidationError):
            Asset(
                name="Battery 1",
                type=AssetType.BATTERY,
                capabilities=[
                    Capability(type=CapabilityType.CHARGE, max_power_kw=3.0),
                    Capability(type=CapabilityType.CHARGE, max_power_kw=5.0),
                ],
            )

    def test_latest_telemetry_must_match_asset_id(self):
        with pytest.raises(ValidationError):
            Asset(
                id="battery-1",
                name="Battery 1",
                type=AssetType.BATTERY,
                latest_telemetry=_telemetry("some-other-asset"),
            )

    def test_latest_telemetry_reference_not_duplicated_fields(self):
        asset = Asset(
            id="battery-1",
            name="Battery 1",
            type=AssetType.BATTERY,
            latest_telemetry=_telemetry("battery-1", soc_percent=55.0),
        )
        assert asset.latest_telemetry.soc_percent == 55.0
        assert not hasattr(asset, "soc_percent")

    def test_serialization_roundtrip(self):
        asset = Asset(
            id="solar-1",
            name="Rooftop Array",
            type=AssetType.SOLAR,
            capabilities=[Capability(type=CapabilityType.GENERATE, max_power_kw=5.0)],
        )
        data = asset.model_dump(mode="json")
        restored = Asset.model_validate(data)
        assert restored == asset

    # Representative examples for every MVP asset type.

    def test_solar_example(self):
        asset = Asset(
            id="solar-1",
            name="Rooftop Array",
            type=AssetType.SOLAR,
            capabilities=[Capability(type=CapabilityType.GENERATE, max_power_kw=5.0)],
        )
        assert asset.type is AssetType.SOLAR

    def test_battery_example(self):
        asset = Asset(
            id="battery-1",
            name="Site Battery",
            type=AssetType.BATTERY,
            capabilities=[
                Capability(type=CapabilityType.CHARGE, max_power_kw=3.5, capacity_kwh=10.0),
                Capability(type=CapabilityType.DISCHARGE, max_power_kw=3.5, capacity_kwh=10.0),
            ],
        )
        assert {c.type for c in asset.capabilities} == {
            CapabilityType.CHARGE,
            CapabilityType.DISCHARGE,
        }

    def test_ev_charger_example(self):
        asset = Asset(
            id="ev-1",
            name="EV Charger Bay 1",
            type=AssetType.EV_CHARGER,
            capabilities=[Capability(type=CapabilityType.CHARGE, max_power_kw=7.2)],
        )
        assert asset.type is AssetType.EV_CHARGER

    def test_flexible_load_example(self):
        asset = Asset(
            id="load-1",
            name="Laundry Room",
            type=AssetType.FLEXIBLE_LOAD,
            capabilities=[
                Capability(type=CapabilityType.CONSUME, max_power_kw=2.0),
                Capability(type=CapabilityType.DEFER, max_power_kw=2.0),
            ],
        )
        assert asset.type is AssetType.FLEXIBLE_LOAD

    def test_critical_load_example(self):
        asset = Asset(
            id="load-critical-1",
            name="ICU Ward",
            type=AssetType.CRITICAL_LOAD,
            capabilities=[Capability(type=CapabilityType.CONSUME, max_power_kw=4.0)],
        )
        assert asset.type is AssetType.CRITICAL_LOAD

    def test_grid_example(self):
        asset = Asset(
            id="grid-1",
            name="Utility Grid Connection",
            type=AssetType.GRID,
            capabilities=[Capability(type=CapabilityType.GENERATE, max_power_kw=1000.0)],
        )
        assert asset.type is AssetType.GRID

    def test_site_example(self):
        asset = Asset(id="site-1", name="Main Campus", type=AssetType.SITE)
        assert asset.capabilities == []
