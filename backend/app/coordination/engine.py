"""The EnerFabric coordination engine: a deterministic, framework-
independent function from a ``CoordinationContext`` (current assets,
active intents, system policies) to a feasible, explainable
``CoordinationRun``.

Design, following the locked principles in CLAUDE.md §5/§18:

1. Hard constraints (availability, capability limits, battery reserve,
   critical-load protection) are applied before any priority-based
   allocation — infeasible actions are never offered in the first
   place, not filtered out afterward.
2. Allocation proceeds in a fixed precedence order — critical loads,
   then battery charge/discharge, then EV charging, then flexible
   loads, then the resulting grid interaction — so higher-priority
   objectives always claim available power before lower-priority ones
   compete for what's left.
3. A shared power ledger (renewable surplus + remaining grid-import
   budget) is threaded through each step, so allocations compete for
   the same real capacity instead of being decided in isolation.
4. Every allocation carries a human-readable ``reason`` and the list of
   constraint names considered — nothing is decided silently, and a
   request that cannot be fully satisfied says so explicitly rather
   than pretending otherwise.

No I/O, no randomness, no hidden state: the same ``CoordinationContext``
always produces the same ``CoordinationRun``. There is deliberately no
optimization solver here — allocation order plus the shared ledger is
enough to make predictable, explainable decisions for the MVP scenarios;
a more sophisticated strategy can replace this module later without
touching the domain model or callers.
"""

from dataclasses import dataclass, field
from datetime import datetime

from app.coordination.constraints import (
    battery_reserve_floor_percent,
    get_capability,
    grid_import_limit_kw,
    is_asset_available,
)
from app.coordination.context import CoordinationContext
from app.domain import (
    Allocation,
    AllocationAction,
    AssetType,
    CapabilityType,
    CoordinationRun,
    CoordinationRunStatus,
    DeferrableIntent,
    MinimumSupplyIntent,
    Priority,
    TargetSocByDeadlineIntent,
    Telemetry,
)

_EPSILON = 1e-9


@dataclass
class _Ledger:
    """Mutable power-accounting state threaded through one coordination
    pass. Not part of the domain model — purely an engine-internal
    bookkeeping device for "what capacity is left to allocate".
    """

    grid_budget_kw: float | None
    grid_available: bool
    solar_kw: float = 0.0
    grid_import_kw: float = 0.0
    battery_discharge_remaining: dict[str, float] = field(default_factory=dict)
    battery_discharge_used: dict[str, float] = field(default_factory=dict)
    battery_discharge_blocked_by_reserve: set[str] = field(default_factory=set)
    battery_reserve_block_relevant: set[str] = field(default_factory=set)

    def grid_headroom_kw(self) -> float:
        """Remaining discretionary grid-import capacity for EV/flexible
        allocation. Zero if there is no available grid asset to draw
        from at all — an unset budget means "no policy limit", not
        "power exists out of nowhere".
        """
        if not self.grid_available:
            return 0.0
        if self.grid_budget_kw is None:
            return float("inf")
        return max(self.grid_budget_kw - self.grid_import_kw, 0.0)


def run_coordination(context: CoordinationContext) -> CoordinationRun:
    """Produce one feasible, explainable allocation plan for the given
    input snapshot. Pure function of ``context`` — no side effects.
    """
    run = CoordinationRun(
        triggered_at=context.now,
        trigger_reason=context.trigger_reason,
        status=CoordinationRunStatus.RUNNING,
        grid_snapshot=_grid_telemetry(context),
    )

    grid_asset = next((a for a in context.assets if a.type == AssetType.GRID), None)
    ledger = _Ledger(
        grid_budget_kw=grid_import_limit_kw(context),
        grid_available=grid_asset is not None and is_asset_available(grid_asset),
    )
    solar_allocations, ledger.solar_kw = _allocate_solar(context, run.id)

    allocations = [
        *solar_allocations,
        *_allocate_critical_loads(context, run.id, ledger),
        *_allocate_batteries(context, run.id, ledger),
        *_allocate_ev_chargers(context, run.id, ledger),
        *_allocate_flexible_loads(context, run.id, ledger),
        *_allocate_grid(context, run.id, ledger),
    ]

    run.allocations = allocations
    run.status = CoordinationRunStatus.COMPLETED
    run.summary = _build_summary(allocations)
    return run


def _grid_telemetry(context: CoordinationContext) -> Telemetry | None:
    grid = next((a for a in context.assets if a.type == AssetType.GRID), None)
    return grid.latest_telemetry if grid else None


def _hold(run_id: str, asset_id: str, reason: str, constraints: list[str]) -> Allocation:
    return Allocation(
        coordination_run_id=run_id,
        asset_id=asset_id,
        action=AllocationAction.HOLD,
        allocated_power_kw=0.0,
        feasible=True,
        reason=reason,
        constraints_considered=constraints,
    )


def _allocate_solar(context: CoordinationContext, run_id: str) -> tuple[list[Allocation], float]:
    allocations: list[Allocation] = []
    pool = 0.0
    for solar in context.assets_of_type(AssetType.SOLAR):
        telemetry = solar.latest_telemetry
        if not is_asset_available(solar) or telemetry is None or telemetry.power_kw <= 0:
            allocations.append(
                _hold(
                    run_id,
                    solar.id,
                    "No generation available from this asset in the current cycle.",
                    ["availability"],
                )
            )
            continue
        generated = telemetry.power_kw
        pool += generated
        allocations.append(
            Allocation(
                coordination_run_id=run_id,
                asset_id=solar.id,
                action=AllocationAction.GENERATE,
                allocated_power_kw=generated,
                feasible=True,
                reason=(
                    f"Generating {generated:.2f} kW; contributes to available renewable "
                    "surplus for other assets."
                ),
                constraints_considered=["availability"],
            )
        )
    return allocations, pool


def _required_supply_kw(context: CoordinationContext, load) -> float:
    for intent in context.intents_for_asset(load.id):
        if isinstance(intent, MinimumSupplyIntent):
            return intent.min_power_kw
    capability = get_capability(load, CapabilityType.CONSUME)
    return capability.min_power_kw if capability else 0.0


def _min_supply_intent_id(context: CoordinationContext, load) -> str | None:
    for intent in context.intents_for_asset(load.id):
        if isinstance(intent, MinimumSupplyIntent):
            return intent.id
    return None


def _init_battery_discharge_capacity(context: CoordinationContext, ledger: _Ledger) -> None:
    for battery in context.assets_of_type(AssetType.BATTERY):
        capability = get_capability(battery, CapabilityType.DISCHARGE)
        if capability is None or not is_asset_available(battery):
            ledger.battery_discharge_remaining[battery.id] = 0.0
            continue
        soc = battery.latest_telemetry.soc_percent if battery.latest_telemetry else None
        reserve_floor = battery_reserve_floor_percent(context, battery)
        if soc is not None and soc <= reserve_floor:
            ledger.battery_discharge_remaining[battery.id] = 0.0
            ledger.battery_discharge_blocked_by_reserve.add(battery.id)
        else:
            ledger.battery_discharge_remaining[battery.id] = capability.max_power_kw


def _allocate_critical_loads(
    context: CoordinationContext, run_id: str, ledger: _Ledger
) -> list[Allocation]:
    _init_battery_discharge_capacity(context, ledger)
    allocations: list[Allocation] = []
    grid = next((a for a in context.assets if a.type == AssetType.GRID), None)
    constraints = ["critical_load_priority", "availability", "battery_reserve", "grid_import_limit"]

    for load in context.assets_of_type(AssetType.CRITICAL_LOAD):
        required = _required_supply_kw(context, load)
        if required <= 0:
            allocations.append(
                _hold(
                    run_id,
                    load.id,
                    "No minimum supply requirement configured for this critical load.",
                    ["critical_load_priority"],
                )
            )
            continue

        if not is_asset_available(load):
            allocations.append(
                Allocation(
                    coordination_run_id=run_id,
                    asset_id=load.id,
                    action=AllocationAction.HOLD,
                    allocated_power_kw=0.0,
                    feasible=False,
                    reason="Critical load asset is unavailable/offline; supply could not be "
                    "verified.",
                    constraints_considered=["critical_load_priority", "availability"],
                )
            )
            continue

        remaining = required
        sources = []

        from_solar = min(remaining, ledger.solar_kw)
        if from_solar > 0:
            ledger.solar_kw -= from_solar
            remaining -= from_solar
            sources.append(f"{from_solar:.2f} kW solar")

        from_battery = 0.0
        for battery in context.assets_of_type(AssetType.BATTERY):
            if remaining <= 0:
                break
            available = ledger.battery_discharge_remaining.get(battery.id, 0.0)
            if available <= 0:
                if battery.id in ledger.battery_discharge_blocked_by_reserve:
                    ledger.battery_reserve_block_relevant.add(battery.id)
                continue
            take = min(remaining, available)
            ledger.battery_discharge_remaining[battery.id] -= take
            ledger.battery_discharge_used[battery.id] = (
                ledger.battery_discharge_used.get(battery.id, 0.0) + take
            )
            remaining -= take
            from_battery += take
        if from_battery > 0:
            sources.append(f"{from_battery:.2f} kW battery discharge")

        from_grid = 0.0
        if remaining > 0 and grid is not None and is_asset_available(grid):
            from_grid = remaining
            ledger.grid_import_kw += from_grid
            remaining -= from_grid
            sources.append(f"{from_grid:.2f} kW grid import")

        served = required - remaining
        feasible = remaining <= _EPSILON
        source_text = ", ".join(sources) if sources else "no available source"
        if feasible:
            reason = (
                f"Critical load fully served at {served:.2f} kW using {source_text}; "
                "protected ahead of lower-priority demand."
            )
        else:
            reason = (
                f"Only {served:.2f} kW of the required {required:.2f} kW could be served "
                f"using {source_text}; no further supply available (grid unavailable and "
                "battery reserve exhausted)."
            )

        allocations.append(
            Allocation(
                coordination_run_id=run_id,
                asset_id=load.id,
                action=AllocationAction.CONSUME,
                allocated_power_kw=served,
                feasible=feasible,
                reason=reason,
                source_intent_id=_min_supply_intent_id(context, load),
                constraints_considered=constraints,
            )
        )

    return allocations


def _allocate_batteries(
    context: CoordinationContext, run_id: str, ledger: _Ledger
) -> list[Allocation]:
    allocations: list[Allocation] = []
    for battery in context.assets_of_type(AssetType.BATTERY):
        used_for_critical = ledger.battery_discharge_used.get(battery.id, 0.0)
        if used_for_critical > 0:
            reserve_floor = battery_reserve_floor_percent(context, battery)
            allocations.append(
                Allocation(
                    coordination_run_id=run_id,
                    asset_id=battery.id,
                    action=AllocationAction.DISCHARGE,
                    allocated_power_kw=used_for_critical,
                    feasible=True,
                    reason=(
                        f"Discharging {used_for_critical:.2f} kW to protect critical load "
                        f"supply, staying above the configured {reserve_floor:.0f}% reserve."
                    ),
                    constraints_considered=["battery_reserve", "capability_max_power"],
                )
            )
            continue

        if not is_asset_available(battery):
            allocations.append(
                _hold(run_id, battery.id, "Battery asset is unavailable/offline.", ["availability"])
            )
            continue

        if battery.id in ledger.battery_reserve_block_relevant:
            reserve_floor = battery_reserve_floor_percent(context, battery)
            allocations.append(
                Allocation(
                    coordination_run_id=run_id,
                    asset_id=battery.id,
                    action=AllocationAction.HOLD,
                    allocated_power_kw=0.0,
                    feasible=False,
                    reason=(
                        "Discharge request rejected: state of charge is at or below the "
                        f"configured {reserve_floor:.0f}% reserve."
                    ),
                    constraints_considered=["battery_reserve"],
                )
            )
            continue

        capability = get_capability(battery, CapabilityType.CHARGE)
        soc = battery.latest_telemetry.soc_percent if battery.latest_telemetry else None
        if capability is not None and ledger.solar_kw > 0 and (soc is None or soc < 100):
            take = min(ledger.solar_kw, capability.max_power_kw)
            ledger.solar_kw -= take
            allocations.append(
                Allocation(
                    coordination_run_id=run_id,
                    asset_id=battery.id,
                    action=AllocationAction.CHARGE,
                    allocated_power_kw=take,
                    feasible=True,
                    reason=f"Charging at {take:.2f} kW using available solar surplus.",
                    constraints_considered=["capability_max_power", "renewable_preference"],
                )
            )
            continue

        allocations.append(
            _hold(
                run_id,
                battery.id,
                "No solar surplus available and no discharge required; holding current state.",
                ["availability"],
            )
        )
    return allocations


def _deadline_feasibility_note(
    context: CoordinationContext,
    charger,
    intent: TargetSocByDeadlineIntent,
    allocated_kw: float,
) -> str | None:
    telemetry = charger.latest_telemetry
    capability = get_capability(charger, CapabilityType.CHARGE)
    if (
        telemetry is None
        or telemetry.soc_percent is None
        or capability is None
        or capability.capacity_kwh is None
    ):
        return None
    hours_remaining = (intent.deadline - context.now).total_seconds() / 3600
    if hours_remaining <= 0:
        return None
    energy_needed_kwh = (
        capability.capacity_kwh * max(intent.target_soc_percent - telemetry.soc_percent, 0) / 100
    )
    if energy_needed_kwh <= 0:
        return "Target SOC has already been reached."
    required_kw = energy_needed_kwh / hours_remaining
    if allocated_kw + _EPSILON >= required_kw:
        return "On track to reach target SOC before the deadline."
    return "At the currently allocated power, target SOC may not be reached by the deadline."


def _priority_sort_key(
    asset_id: str, intents_by_asset: dict, priority_fallback: Priority = Priority.LOW
):
    intent = intents_by_asset.get(asset_id)
    priority = intent.priority.value if intent is not None else priority_fallback.value
    return (priority, asset_id)


def _allocate_ev_chargers(
    context: CoordinationContext, run_id: str, ledger: _Ledger
) -> list[Allocation]:
    allocations: list[Allocation] = []
    chargers = context.assets_of_type(AssetType.EV_CHARGER)
    intents_by_asset: dict[str, TargetSocByDeadlineIntent] = {
        intent.asset_id: intent
        for intent in context.intents
        if isinstance(intent, TargetSocByDeadlineIntent)
    }
    ordered = sorted(
        chargers,
        key=lambda a: _priority_sort_key(a.id, intents_by_asset),
    )

    for charger in ordered:
        intent = intents_by_asset.get(charger.id)
        capability = get_capability(charger, CapabilityType.CHARGE)

        if not is_asset_available(charger):
            allocations.append(
                Allocation(
                    coordination_run_id=run_id,
                    asset_id=charger.id,
                    action=AllocationAction.HOLD,
                    allocated_power_kw=0.0,
                    feasible=intent is None,
                    reason="EV charger is unavailable/offline; charging could not be allocated.",
                    source_intent_id=intent.id if intent else None,
                    constraints_considered=["availability"],
                )
            )
            continue
        if capability is None:
            allocations.append(
                _hold(
                    run_id,
                    charger.id,
                    "EV charger has no configured charge capability.",
                    ["capability_max_power"],
                )
            )
            continue
        if intent is None:
            allocations.append(
                _hold(run_id, charger.id, "No charging intent declared for this cycle.", [])
            )
            continue
        if context.now >= intent.deadline:
            allocations.append(
                Allocation(
                    coordination_run_id=run_id,
                    asset_id=charger.id,
                    action=AllocationAction.HOLD,
                    allocated_power_kw=0.0,
                    feasible=False,
                    reason="Charging deadline has already passed; no further allocation made "
                    "this cycle.",
                    source_intent_id=intent.id,
                    constraints_considered=["deadline"],
                )
            )
            continue

        desired = capability.max_power_kw
        from_solar = min(desired, ledger.solar_kw)
        ledger.solar_kw -= from_solar
        remaining = desired - from_solar

        from_grid = min(remaining, ledger.grid_headroom_kw()) if remaining > 0 else 0.0
        ledger.grid_import_kw += from_grid
        remaining -= from_grid

        allocated = from_solar + from_grid
        if allocated <= 0:
            allocations.append(
                Allocation(
                    coordination_run_id=run_id,
                    asset_id=charger.id,
                    action=AllocationAction.HOLD,
                    allocated_power_kw=0.0,
                    feasible=False,
                    reason=(
                        "Charging deferred: no solar surplus available and the grid import "
                        "limit is exhausted."
                    ),
                    source_intent_id=intent.id,
                    constraints_considered=["grid_import_limit", "capability_max_power"],
                )
            )
            continue

        sources = []
        if from_solar > 0:
            sources.append(f"{from_solar:.2f} kW solar")
        if from_grid > 0:
            sources.append(f"{from_grid:.2f} kW grid")

        reason = f"EV charging allocated at {allocated:.2f} kW using {', '.join(sources)}."
        deadline_note = _deadline_feasibility_note(context, charger, intent, allocated)
        if deadline_note:
            reason += f" {deadline_note}"

        allocations.append(
            Allocation(
                coordination_run_id=run_id,
                asset_id=charger.id,
                action=AllocationAction.CHARGE,
                allocated_power_kw=allocated,
                target_soc_percent=intent.target_soc_percent,
                feasible=True,
                reason=reason,
                source_intent_id=intent.id,
                constraints_considered=[
                    "capability_max_power",
                    "grid_import_limit",
                    "renewable_preference",
                ],
            )
        )
    return allocations


def _within_window(now: datetime, intent: DeferrableIntent) -> bool:
    if intent.window_start is not None and now < intent.window_start:
        return False
    return not (intent.window_end is not None and now > intent.window_end)


def _allocate_flexible_loads(
    context: CoordinationContext, run_id: str, ledger: _Ledger
) -> list[Allocation]:
    allocations: list[Allocation] = []
    loads = context.assets_of_type(AssetType.FLEXIBLE_LOAD)
    intents_by_asset: dict[str, DeferrableIntent] = {
        intent.asset_id: intent
        for intent in context.intents
        if isinstance(intent, DeferrableIntent)
    }
    ordered = sorted(
        loads,
        key=lambda a: _priority_sort_key(a.id, intents_by_asset),
    )

    for load in ordered:
        intent = intents_by_asset.get(load.id)
        capability = get_capability(load, CapabilityType.CONSUME) or get_capability(
            load, CapabilityType.DEFER
        )

        if not is_asset_available(load):
            allocations.append(
                Allocation(
                    coordination_run_id=run_id,
                    asset_id=load.id,
                    action=AllocationAction.HOLD,
                    allocated_power_kw=0.0,
                    feasible=False,
                    reason="Flexible load asset is unavailable/offline; could not be run "
                    "this cycle.",
                    source_intent_id=intent.id if intent else None,
                    constraints_considered=["availability"],
                )
            )
            continue
        if capability is None:
            allocations.append(
                _hold(
                    run_id,
                    load.id,
                    "Flexible load has no configured consume capability.",
                    ["capability_max_power"],
                )
            )
            continue
        if intent is not None and not _within_window(context.now, intent):
            allocations.append(
                Allocation(
                    coordination_run_id=run_id,
                    asset_id=load.id,
                    action=AllocationAction.DEFER,
                    allocated_power_kw=0.0,
                    feasible=True,
                    reason="Deferred: outside the declared allowable window for this load.",
                    source_intent_id=intent.id,
                    constraints_considered=["deferral_window"],
                )
            )
            continue

        desired = capability.max_power_kw
        from_solar = min(desired, ledger.solar_kw)
        ledger.solar_kw -= from_solar
        remaining = desired - from_solar

        from_grid = min(remaining, ledger.grid_headroom_kw()) if remaining > 0 else 0.0
        ledger.grid_import_kw += from_grid
        remaining -= from_grid

        allocated = from_solar + from_grid
        if allocated <= 0:
            allocations.append(
                Allocation(
                    coordination_run_id=run_id,
                    asset_id=load.id,
                    action=AllocationAction.DEFER,
                    allocated_power_kw=0.0,
                    feasible=True,
                    reason="Flexible load deferred because the grid import limit would "
                    "otherwise be exceeded.",
                    source_intent_id=intent.id if intent else None,
                    constraints_considered=["grid_import_limit"],
                )
            )
            continue

        sources = []
        if from_solar > 0:
            sources.append(f"{from_solar:.2f} kW solar")
        if from_grid > 0:
            sources.append(f"{from_grid:.2f} kW grid")

        allocations.append(
            Allocation(
                coordination_run_id=run_id,
                asset_id=load.id,
                action=AllocationAction.CONSUME,
                allocated_power_kw=allocated,
                feasible=True,
                reason=f"Flexible load run at {allocated:.2f} kW using {', '.join(sources)}.",
                source_intent_id=intent.id if intent else None,
                constraints_considered=["capability_max_power", "grid_import_limit"],
            )
        )
    return allocations


def _allocate_grid(context: CoordinationContext, run_id: str, ledger: _Ledger) -> list[Allocation]:
    grid = next((a for a in context.assets if a.type == AssetType.GRID), None)
    if grid is None:
        return []

    net_import = ledger.grid_import_kw - ledger.solar_kw
    limit = ledger.grid_budget_kw

    if net_import > _EPSILON:
        feasible = limit is None or net_import <= limit + _EPSILON
        if feasible:
            reason = (
                f"Net grid import of {net_import:.2f} kW covers demand not met by solar "
                "or battery."
            )
        else:
            reason = (
                f"Grid import of {net_import:.2f} kW exceeds the configured {limit:.2f} kW "
                "limit; critical load protection was prioritized over the import limit."
            )
        return [
            Allocation(
                coordination_run_id=run_id,
                asset_id=grid.id,
                action=AllocationAction.GENERATE,
                allocated_power_kw=net_import,
                feasible=feasible,
                reason=reason,
                constraints_considered=["grid_import_limit"],
            )
        ]

    if net_import < -_EPSILON:
        export = -net_import
        return [
            Allocation(
                coordination_run_id=run_id,
                asset_id=grid.id,
                action=AllocationAction.CONSUME,
                allocated_power_kw=export,
                feasible=True,
                reason=f"Exporting {export:.2f} kW of unused renewable surplus to the grid.",
                constraints_considered=["renewable_preference"],
            )
        ]

    return [_hold(run_id, grid.id, "Site power balanced; no grid import or export required.", [])]


def _build_summary(allocations: list[Allocation]) -> str:
    total = len(allocations)
    infeasible = [a for a in allocations if not a.feasible]
    if not infeasible:
        return (
            f"{total} allocation(s) decided; all requirements were met within available capacity."
        )
    names = ", ".join(sorted({a.asset_id for a in infeasible}))
    return (
        f"{total} allocation(s) decided; {len(infeasible)} could not be fully satisfied "
        f"(assets: {names}) — see individual allocation reasons for the conflicting constraint."
    )
