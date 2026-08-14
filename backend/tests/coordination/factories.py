"""Small builder helpers for constructing domain objects in coordination
engine tests. Every builder fills in a sensible default for every
required field so a test only has to override what it actually cares
about.
"""

from datetime import UTC, datetime

from app.domain import (
    Asset,
    AssetType,
    Capability,
    CapabilityType,
    DeferrableIntent,
    MinimumReserveIntent,
    MinimumSupplyIntent,
    OperatingState,
    Policy,
    PolicyType,
    Priority,
    TargetSocByDeadlineIntent,
    Telemetry,
)

NOW = datetime(2026, 8, 13, 18, 0, tzinfo=UTC)


def telemetry(asset_id: str, **overrides) -> Telemetry:
    defaults = dict(
        asset_id=asset_id,
        timestamp=NOW,
        power_kw=0.0,
        available=True,
        operating_state=OperatingState.ONLINE,
    )
    defaults.update(overrides)
    return Telemetry(**defaults)


def solar_asset(
    asset_id: str = "solar-1", *, generating_kw: float = 5.0, **telemetry_overrides
) -> Asset:
    defaults = dict(power_kw=generating_kw, operating_state=OperatingState.ACTIVE)
    defaults.update(telemetry_overrides)
    return Asset(
        id=asset_id,
        name="Rooftop Solar",
        type=AssetType.SOLAR,
        capabilities=[Capability(type=CapabilityType.GENERATE, max_power_kw=20.0)],
        latest_telemetry=telemetry(asset_id, **defaults),
    )


def battery_asset(
    asset_id: str = "battery-1",
    *,
    soc_percent: float = 60.0,
    max_charge_kw: float = 5.0,
    max_discharge_kw: float = 5.0,
    capacity_kwh: float = 20.0,
    **telemetry_overrides,
) -> Asset:
    defaults = dict(power_kw=0.0, soc_percent=soc_percent, operating_state=OperatingState.IDLE)
    defaults.update(telemetry_overrides)
    return Asset(
        id=asset_id,
        name="Site Battery",
        type=AssetType.BATTERY,
        capabilities=[
            Capability(
                type=CapabilityType.CHARGE, max_power_kw=max_charge_kw, capacity_kwh=capacity_kwh
            ),
            Capability(
                type=CapabilityType.DISCHARGE,
                max_power_kw=max_discharge_kw,
                capacity_kwh=capacity_kwh,
            ),
        ],
        latest_telemetry=telemetry(asset_id, **defaults),
    )


def ev_charger_asset(
    asset_id: str = "ev-1",
    *,
    max_power_kw: float = 7.0,
    capacity_kwh: float = 60.0,
    **telemetry_overrides,
) -> Asset:
    defaults = dict(power_kw=0.0, soc_percent=40.0, operating_state=OperatingState.IDLE)
    defaults.update(telemetry_overrides)
    return Asset(
        id=asset_id,
        name="EV Charger",
        type=AssetType.EV_CHARGER,
        capabilities=[
            Capability(
                type=CapabilityType.CHARGE, max_power_kw=max_power_kw, capacity_kwh=capacity_kwh
            )
        ],
        latest_telemetry=telemetry(asset_id, **defaults),
    )


def flexible_load_asset(
    asset_id: str = "flex-1", *, max_power_kw: float = 3.0, **telemetry_overrides
) -> Asset:
    defaults = dict(power_kw=0.0)
    defaults.update(telemetry_overrides)
    return Asset(
        id=asset_id,
        name="Flexible Load",
        type=AssetType.FLEXIBLE_LOAD,
        capabilities=[Capability(type=CapabilityType.CONSUME, max_power_kw=max_power_kw)],
        latest_telemetry=telemetry(asset_id, **defaults),
    )


def critical_load_asset(
    asset_id: str = "crit-1", *, max_power_kw: float = 4.0, **telemetry_overrides
) -> Asset:
    defaults = dict(power_kw=0.0)
    defaults.update(telemetry_overrides)
    return Asset(
        id=asset_id,
        name="Critical Load",
        type=AssetType.CRITICAL_LOAD,
        capabilities=[Capability(type=CapabilityType.CONSUME, max_power_kw=max_power_kw)],
        latest_telemetry=telemetry(asset_id, **defaults),
    )


def grid_asset(asset_id: str = "grid-1", **telemetry_overrides) -> Asset:
    defaults = dict(power_kw=0.0)
    defaults.update(telemetry_overrides)
    return Asset(
        id=asset_id,
        name="Grid Connection",
        type=AssetType.GRID,
        latest_telemetry=telemetry(asset_id, **defaults),
    )


def target_soc_intent(
    asset_id: str, *, target_soc_percent: float = 80.0, deadline=None, **overrides
):
    return TargetSocByDeadlineIntent(
        asset_id=asset_id,
        description=f"Charge {asset_id} to {target_soc_percent}%",
        target_soc_percent=target_soc_percent,
        deadline=deadline or datetime(2026, 8, 14, 7, 0, tzinfo=UTC),
        **overrides,
    )


def minimum_reserve_intent(asset_id: str, *, min_soc_percent: float = 30.0, **overrides):
    return MinimumReserveIntent(
        asset_id=asset_id,
        description=f"Maintain at least {min_soc_percent}% reserve on {asset_id}",
        min_soc_percent=min_soc_percent,
        **overrides,
    )


def minimum_supply_intent(asset_id: str, *, min_power_kw: float = 2.0, **overrides):
    return MinimumSupplyIntent(
        asset_id=asset_id,
        description=f"Maintain at least {min_power_kw} kW supply to {asset_id}",
        min_power_kw=min_power_kw,
        **overrides,
    )


def deferrable_intent(asset_id: str, **overrides):
    return DeferrableIntent(
        asset_id=asset_id,
        description=f"{asset_id} may be deferred",
        **overrides,
    )


def policy(policy_type: PolicyType, **overrides) -> Policy:
    defaults = dict(description=f"{policy_type.value} policy", priority=Priority.HIGH)
    defaults.update(overrides)
    return Policy(type=policy_type, **defaults)
