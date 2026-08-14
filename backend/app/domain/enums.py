"""Enumerations shared across the EnerFabric domain model."""

from enum import IntEnum, StrEnum


class AssetType(StrEnum):
    """What kind of resource an Asset is.

    SITE is a system-level pseudo-asset (a campus/site as a whole)
    rather than a physical DER — it exists so that site-wide intents
    (e.g. "prefer renewable energy") have a concrete asset to attach
    to, consistent with Asset representing "a distributed energy
    resource or system-level resource."
    """

    SOLAR = "solar"
    BATTERY = "battery"
    EV_CHARGER = "ev_charger"
    FLEXIBLE_LOAD = "flexible_load"
    CRITICAL_LOAD = "critical_load"
    GRID = "grid"
    SITE = "site"


class CapabilityType(StrEnum):
    """What an asset is physically/operationally able to do."""

    GENERATE = "generate"
    CONSUME = "consume"
    CHARGE = "charge"
    DISCHARGE = "discharge"
    CURTAIL = "curtail"
    DEFER = "defer"


class OperatingState(StrEnum):
    """Observed operating state of an asset, as reported by telemetry."""

    ONLINE = "online"
    OFFLINE = "offline"
    FAULT = "fault"
    IDLE = "idle"
    ACTIVE = "active"


class Priority(IntEnum):
    """Relative importance, used by the future coordination engine for
    priority-based scoring. Lower value = higher priority.
    """

    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


class IntentType(StrEnum):
    """The small set of canonical intent "shapes" EnerFabric reasons
    about. New concrete intents are expressed by adding a new subclass
    for one of these types (or, if genuinely novel, a new type here)
    without changing existing intent classes.
    """

    TARGET_SOC_BY_DEADLINE = "target_soc_by_deadline"
    MINIMUM_RESERVE = "minimum_reserve"
    MINIMUM_SUPPLY = "minimum_supply"
    DEFERRABLE = "deferrable"
    PREFER_RENEWABLE = "prefer_renewable"


class PolicyType(StrEnum):
    """System-level rules the coordination engine must honor, distinct
    from any single asset's intent.
    """

    PROTECT_CRITICAL_LOADS = "protect_critical_loads"
    MAINTAIN_BATTERY_RESERVE = "maintain_battery_reserve"
    LIMIT_GRID_IMPORT = "limit_grid_import"
    PREFER_RENEWABLE_ENERGY = "prefer_renewable_energy"
    REDUCE_PEAK_DEMAND = "reduce_peak_demand"


class AllocationAction(StrEnum):
    """The action EnerFabric decided an asset should take."""

    CHARGE = "charge"
    DISCHARGE = "discharge"
    CONSUME = "consume"
    GENERATE = "generate"
    CURTAIL = "curtail"
    DEFER = "defer"
    HOLD = "hold"


class CoordinationRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TriggerReason(StrEnum):
    """What caused a CoordinationRun to be triggered. Covers the three
    MVP scenarios plus general-purpose triggers.
    """

    SOLAR_SURPLUS = "solar_surplus"
    PEAK_DEMAND = "peak_demand"
    GRID_OUTAGE = "grid_outage"
    SCHEDULED = "scheduled"
    MANUAL = "manual"
