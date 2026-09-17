"""Centrally-evaluated constraint helpers for the coordination engine.

Constraints (availability, capability limits, battery reserve, grid
import limits) are looked up here rather than hard-coded inside
per-asset-type logic in ``engine.py``, so every rule the engine honors
stays auditable in one place instead of scattered across allocation
functions.
"""

from app.coordination.context import CoordinationContext
from app.domain import (
    Asset,
    Capability,
    CapabilityType,
    MinimumReserveIntent,
    OperatingState,
    PolicyType,
)

_UNAVAILABLE_STATES = {OperatingState.OFFLINE, OperatingState.FAULT}


def is_asset_available(asset: Asset) -> bool:
    """An asset is usable this cycle only if it has telemetry reporting
    it as available and not offline/faulted. No telemetry means its
    state cannot be verified, so it is treated as unavailable.
    """
    telemetry = asset.latest_telemetry
    if telemetry is None:
        return False
    if not telemetry.available:
        return False
    return telemetry.operating_state not in _UNAVAILABLE_STATES


def get_capability(asset: Asset, capability_type: CapabilityType) -> Capability | None:
    return next((c for c in asset.capabilities if c.type == capability_type), None)


def grid_import_limit_kw(context: CoordinationContext) -> float | None:
    """The site's grid-import budget for this cycle, or ``None`` if
    unlimited. LIMIT_GRID_IMPORT and REDUCE_PEAK_DEMAND both express
    this as a threshold_kw; the tighter of the two (enabled) policies
    wins.
    """
    thresholds = [
        p.threshold_kw
        for p in (
            context.enabled_policies_of_type(PolicyType.LIMIT_GRID_IMPORT)
            + context.enabled_policies_of_type(PolicyType.REDUCE_PEAK_DEMAND)
        )
        if p.threshold_kw is not None
    ]
    return min(thresholds) if thresholds else None


def battery_reserve_floor_percent(context: CoordinationContext, battery: Asset) -> float:
    """The minimum SOC this battery must not be discharged below.

    An asset-specific MinimumReserveIntent takes precedence over the
    system-wide MAINTAIN_BATTERY_RESERVE policy; if neither is present
    the floor is 0 (no reserve protection configured).
    """
    for intent in context.intents_for_asset(battery.id):
        if isinstance(intent, MinimumReserveIntent):
            return intent.min_soc_percent
    for policy in context.enabled_policies_of_type(PolicyType.MAINTAIN_BATTERY_RESERVE):
        if policy.threshold_percent is not None:
            return policy.threshold_percent
    return 0.0
