"""Static configuration for each simulated DER type.

Each config is a frozen dataclass — not a domain/persistence model —
describing a single simulated device's fixed parameters (capacity,
power limits, schedule windows) plus how to describe itself as a
domain ``Capability`` list, so ``simulator.py`` can build
domain-compatible ``Asset`` objects without per-asset-type branching
living outside this module. Validated eagerly in ``__post_init__`` so
an invalid config fails at construction, not at some later simulation
step.
"""

from dataclasses import dataclass
from typing import ClassVar

from app.domain import AssetType, Capability, CapabilityType


@dataclass(frozen=True)
class SolarConfig:
    """A rooftop/site solar array with a deterministic daylight-hours
    generation profile (see ``profiles.step_solar``).
    """

    asset_id: str
    name: str = "Rooftop Solar"
    max_power_kw: float = 10.0
    sunrise_hour: float = 6.0
    sunset_hour: float = 18.0

    asset_type: ClassVar[AssetType] = AssetType.SOLAR

    def __post_init__(self) -> None:
        if self.max_power_kw <= 0:
            raise ValueError("max_power_kw must be positive")
        if not 0 <= self.sunrise_hour < self.sunset_hour <= 24:
            raise ValueError("sunrise_hour must be before sunset_hour, both within [0, 24]")

    def capabilities(self) -> list[Capability]:
        return [Capability(type=CapabilityType.GENERATE, max_power_kw=self.max_power_kw)]


@dataclass(frozen=True)
class BatteryConfig:
    """A site battery that charges during ``charge_window`` (typically
    solar hours) and discharges during ``discharge_window`` (typically
    evening peak), never crossing ``reserve_percent`` on the way down.
    """

    asset_id: str
    name: str = "Site Battery"
    max_charge_kw: float = 5.0
    max_discharge_kw: float = 5.0
    capacity_kwh: float = 20.0
    reserve_percent: float = 10.0
    initial_soc_percent: float = 50.0
    charge_window: tuple[float, float] = (9.0, 15.0)
    discharge_window: tuple[float, float] = (18.0, 22.0)

    asset_type: ClassVar[AssetType] = AssetType.BATTERY

    def __post_init__(self) -> None:
        if self.max_charge_kw <= 0 or self.max_discharge_kw <= 0 or self.capacity_kwh <= 0:
            raise ValueError("max_charge_kw, max_discharge_kw, and capacity_kwh must be positive")
        if not 0 <= self.reserve_percent <= 100:
            raise ValueError("reserve_percent must be within [0, 100]")
        if not 0 <= self.initial_soc_percent <= 100:
            raise ValueError("initial_soc_percent must be within [0, 100]")
        for start, end in (self.charge_window, self.discharge_window):
            if not 0 <= start < end <= 24:
                raise ValueError("charge_window/discharge_window must be ordered, within [0, 24]")

    def capabilities(self) -> list[Capability]:
        return [
            Capability(
                type=CapabilityType.CHARGE,
                max_power_kw=self.max_charge_kw,
                capacity_kwh=self.capacity_kwh,
            ),
            Capability(
                type=CapabilityType.DISCHARGE,
                max_power_kw=self.max_discharge_kw,
                capacity_kwh=self.capacity_kwh,
            ),
        ]


@dataclass(frozen=True)
class EVChargerConfig:
    """An EV charger that charges toward 100% SOC whenever it isn't
    already there. No connect/disconnect session modeling in this MVP —
    the EV is treated as continuously present (see ``profiles.py``).
    """

    asset_id: str
    name: str = "EV Charger"
    max_power_kw: float = 7.0
    capacity_kwh: float = 60.0
    initial_soc_percent: float = 40.0

    asset_type: ClassVar[AssetType] = AssetType.EV_CHARGER

    def __post_init__(self) -> None:
        if self.max_power_kw <= 0 or self.capacity_kwh <= 0:
            raise ValueError("max_power_kw and capacity_kwh must be positive")
        if not 0 <= self.initial_soc_percent <= 100:
            raise ValueError("initial_soc_percent must be within [0, 100]")

    def capabilities(self) -> list[Capability]:
        return [
            Capability(
                type=CapabilityType.CHARGE,
                max_power_kw=self.max_power_kw,
                capacity_kwh=self.capacity_kwh,
            )
        ]


@dataclass(frozen=True)
class FlexibleLoadConfig:
    """A controllable, deferrable load that draws its full demand during
    ``active_window`` and nothing outside it.
    """

    asset_id: str
    name: str = "Flexible Load"
    max_power_kw: float = 3.0
    active_window: tuple[float, float] = (9.0, 17.0)

    asset_type: ClassVar[AssetType] = AssetType.FLEXIBLE_LOAD

    def __post_init__(self) -> None:
        if self.max_power_kw <= 0:
            raise ValueError("max_power_kw must be positive")
        start, end = self.active_window
        if not 0 <= start < end <= 24:
            raise ValueError("active_window must be ordered (start, end), within [0, 24]")

    def capabilities(self) -> list[Capability]:
        return [Capability(type=CapabilityType.CONSUME, max_power_kw=self.max_power_kw)]


@dataclass(frozen=True)
class CriticalLoadConfig:
    """A mandatory load: demand is never zero, and rises to
    ``peak_power_kw`` during ``peak_window``.
    """

    asset_id: str
    name: str = "Critical Load"
    base_power_kw: float = 2.0
    peak_power_kw: float = 4.0
    peak_window: tuple[float, float] = (18.0, 22.0)

    asset_type: ClassVar[AssetType] = AssetType.CRITICAL_LOAD

    def __post_init__(self) -> None:
        if self.base_power_kw <= 0 or self.peak_power_kw <= 0:
            raise ValueError("base_power_kw and peak_power_kw must be positive")
        if self.peak_power_kw < self.base_power_kw:
            raise ValueError("peak_power_kw must be at least base_power_kw")
        start, end = self.peak_window
        if not 0 <= start < end <= 24:
            raise ValueError("peak_window must be ordered (start, end), within [0, 24]")

    def capabilities(self) -> list[Capability]:
        return [Capability(type=CapabilityType.CONSUME, max_power_kw=self.peak_power_kw)]


@dataclass(frozen=True)
class GridConfig:
    """The site's grid connection. Has no ``Capability`` of its own
    (matches the domain convention of a capability-less grid asset,
    e.g. ``tests/coordination/factories.py::grid_asset``) — its role is
    to absorb whatever the rest of the fleet could not balance itself,
    within its configured import/export limits (see
    ``profiles.step_grid``).
    """

    asset_id: str
    name: str = "Grid Connection"
    import_limit_kw: float | None = None
    export_limit_kw: float | None = None
    available: bool = True

    asset_type: ClassVar[AssetType] = AssetType.GRID

    def __post_init__(self) -> None:
        if self.import_limit_kw is not None and self.import_limit_kw < 0:
            raise ValueError("import_limit_kw must not be negative")
        if self.export_limit_kw is not None and self.export_limit_kw < 0:
            raise ValueError("export_limit_kw must not be negative")

    def capabilities(self) -> list[Capability]:
        return []


DeviceConfig = (
    SolarConfig
    | BatteryConfig
    | EVChargerConfig
    | FlexibleLoadConfig
    | CriticalLoadConfig
    | GridConfig
)
