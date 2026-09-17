from app.coordination.constraints import (
    battery_reserve_floor_percent,
    get_capability,
    grid_import_limit_kw,
    is_asset_available,
)
from app.coordination.context import CoordinationContext
from app.domain import CapabilityType, OperatingState, PolicyType
from tests.coordination.factories import (
    battery_asset,
    minimum_reserve_intent,
    policy,
    solar_asset,
)


class TestIsAssetAvailable:
    def test_available_when_online_and_telemetry_available(self):
        asset = solar_asset(available=True, operating_state=OperatingState.ACTIVE)
        assert is_asset_available(asset) is True

    def test_unavailable_when_no_telemetry(self):
        asset = solar_asset()
        asset = asset.model_copy(update={"latest_telemetry": None})
        assert is_asset_available(asset) is False

    def test_unavailable_when_telemetry_marks_unavailable(self):
        asset = solar_asset(available=False)
        assert is_asset_available(asset) is False

    def test_unavailable_when_offline(self):
        asset = solar_asset(operating_state=OperatingState.OFFLINE)
        assert is_asset_available(asset) is False

    def test_unavailable_when_fault(self):
        asset = solar_asset(operating_state=OperatingState.FAULT)
        assert is_asset_available(asset) is False


class TestGetCapability:
    def test_returns_matching_capability(self):
        asset = battery_asset()
        cap = get_capability(asset, CapabilityType.CHARGE)
        assert cap is not None
        assert cap.type == CapabilityType.CHARGE

    def test_returns_none_when_missing(self):
        asset = solar_asset()
        assert get_capability(asset, CapabilityType.DISCHARGE) is None


class TestGridImportLimitKw:
    def test_none_when_no_policy(self):
        context = CoordinationContext(assets=[])
        assert grid_import_limit_kw(context) is None

    def test_uses_limit_grid_import_threshold(self):
        context = CoordinationContext(
            assets=[], policies=[policy(PolicyType.LIMIT_GRID_IMPORT, threshold_kw=15)]
        )
        assert grid_import_limit_kw(context) == 15

    def test_takes_the_tighter_of_both_policies(self):
        context = CoordinationContext(
            assets=[],
            policies=[
                policy(PolicyType.LIMIT_GRID_IMPORT, threshold_kw=15),
                policy(PolicyType.REDUCE_PEAK_DEMAND, threshold_kw=8),
            ],
        )
        assert grid_import_limit_kw(context) == 8

    def test_ignores_disabled_policy(self):
        context = CoordinationContext(
            assets=[],
            policies=[policy(PolicyType.LIMIT_GRID_IMPORT, threshold_kw=15, enabled=False)],
        )
        assert grid_import_limit_kw(context) is None


class TestBatteryReserveFloorPercent:
    def test_zero_when_unconfigured(self):
        battery = battery_asset()
        context = CoordinationContext(assets=[battery])
        assert battery_reserve_floor_percent(context, battery) == 0.0

    def test_intent_takes_precedence_over_policy(self):
        battery = battery_asset()
        context = CoordinationContext(
            assets=[battery],
            intents=[minimum_reserve_intent(battery.id, min_soc_percent=35)],
            policies=[policy(PolicyType.MAINTAIN_BATTERY_RESERVE, threshold_percent=10)],
        )
        assert battery_reserve_floor_percent(context, battery) == 35

    def test_falls_back_to_policy(self):
        battery = battery_asset()
        context = CoordinationContext(
            assets=[battery],
            policies=[policy(PolicyType.MAINTAIN_BATTERY_RESERVE, threshold_percent=20)],
        )
        assert battery_reserve_floor_percent(context, battery) == 20
