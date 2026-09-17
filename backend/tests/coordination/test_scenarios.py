"""End-to-end tests for the three MVP scenarios documented in
CLAUDE.md §6: Solar Surplus / EV charging, Battery reserve / peak
constraint, and Grid Outage / critical load protection. These exercise
the engine the way the demo will: a realistic multi-asset snapshot in,
a full CoordinationRun out.
"""

from datetime import UTC, datetime

from app.coordination import CoordinationContext, run_coordination
from app.domain import (
    AllocationAction,
    CoordinationRunStatus,
    OperatingState,
    PolicyType,
    TriggerReason,
)
from tests.coordination.factories import (
    NOW,
    battery_asset,
    critical_load_asset,
    deferrable_intent,
    ev_charger_asset,
    flexible_load_asset,
    grid_asset,
    minimum_reserve_intent,
    minimum_supply_intent,
    policy,
    solar_asset,
    target_soc_intent,
)


def _allocation_for(run, asset_id):
    matches = [a for a in run.allocations if a.asset_id == asset_id]
    assert matches, f"no allocation produced for {asset_id}"
    return matches[0]


class TestScenarioOneEvCharging:
    """Solar generation, a battery holding reserve, an EV with a
    target-SOC-by-deadline intent, and grid/site constraints: the
    engine should produce a feasible charging allocation and explain
    the chosen power level.
    """

    def test_ev_charges_from_solar_surplus_and_explains_the_power_level(self):
        solar = solar_asset(generating_kw=5.0)
        battery = battery_asset(soc_percent=55.0, max_charge_kw=3.0)
        ev = ev_charger_asset(max_power_kw=4.0, soc_percent=40.0)
        grid = grid_asset()

        context = CoordinationContext(
            assets=[solar, battery, ev, grid],
            intents=[
                target_soc_intent(
                    ev.id, target_soc_percent=80.0, deadline=datetime(2026, 8, 14, 7, 0, tzinfo=UTC)
                ),
                minimum_reserve_intent(battery.id, min_soc_percent=30.0),
            ],
            policies=[policy(PolicyType.PREFER_RENEWABLE_ENERGY)],
            trigger_reason=TriggerReason.SOLAR_SURPLUS,
            now=NOW,
        )

        run = run_coordination(context)

        assert run.status == CoordinationRunStatus.COMPLETED
        ev_alloc = _allocation_for(run, ev.id)
        assert ev_alloc.action == AllocationAction.CHARGE
        assert ev_alloc.feasible is True
        assert ev_alloc.allocated_power_kw == 4.0
        assert "4.00 kW" in ev_alloc.reason
        assert "solar" in ev_alloc.reason.lower()
        assert ev_alloc.target_soc_percent == 80.0


class TestScenarioTwoBatteryReserve:
    """Battery SOC, charge/discharge capability, a reserve requirement,
    and a grid/site constraint: the engine must never discharge the
    battery below its configured reserve, and must explain a
    rejected/reduced discharge.
    """

    def test_discharge_reduced_to_zero_when_at_reserve_floor(self):
        battery = battery_asset(soc_percent=30.0, max_discharge_kw=5.0)
        critical = critical_load_asset(max_power_kw=4.0)

        context = CoordinationContext(
            assets=[battery, critical],
            intents=[
                minimum_reserve_intent(battery.id, min_soc_percent=30.0),
                minimum_supply_intent(critical.id, min_power_kw=4.0),
            ],
            trigger_reason=TriggerReason.PEAK_DEMAND,
            now=NOW,
        )

        run = run_coordination(context)

        battery_alloc = _allocation_for(run, battery.id)
        assert battery_alloc.action == AllocationAction.HOLD
        assert battery_alloc.allocated_power_kw == 0.0
        assert "reserve" in battery_alloc.reason.lower()

        critical_alloc = _allocation_for(run, critical.id)
        assert critical_alloc.feasible is False

    def test_discharge_capped_above_reserve_not_unlimited(self):
        battery = battery_asset(soc_percent=40.0, max_discharge_kw=3.0)
        critical = critical_load_asset(max_power_kw=10.0)

        context = CoordinationContext(
            assets=[battery, critical],
            intents=[
                minimum_reserve_intent(battery.id, min_soc_percent=30.0),
                minimum_supply_intent(critical.id, min_power_kw=10.0),
            ],
            trigger_reason=TriggerReason.PEAK_DEMAND,
            now=NOW,
        )

        run = run_coordination(context)

        battery_alloc = _allocation_for(run, battery.id)
        assert battery_alloc.action == AllocationAction.DISCHARGE
        assert battery_alloc.allocated_power_kw == 3.0

        critical_alloc = _allocation_for(run, critical.id)
        assert critical_alloc.allocated_power_kw == 3.0
        assert critical_alloc.feasible is False
        assert "3.00 kW of the required 10.00 kW" in critical_alloc.reason


class TestScenarioThreeCriticalLoadProtection:
    """Grid outage: critical load must stay supplied whenever the
    available system state makes that possible, ahead of any
    lower-priority flexible objective, and a genuinely infeasible
    request must be reported rather than silently satisfied.
    """

    def test_critical_load_protected_using_solar_and_battery_during_outage(self):
        solar = solar_asset(generating_kw=2.0)
        battery = battery_asset(soc_percent=70.0, max_discharge_kw=5.0)
        critical = critical_load_asset(max_power_kw=4.0)
        grid = grid_asset(available=False, operating_state=OperatingState.OFFLINE)

        context = CoordinationContext(
            assets=[solar, battery, critical, grid],
            intents=[
                minimum_reserve_intent(battery.id, min_soc_percent=30.0),
                minimum_supply_intent(critical.id, min_power_kw=4.0),
            ],
            trigger_reason=TriggerReason.GRID_OUTAGE,
            now=NOW,
        )

        run = run_coordination(context)

        critical_alloc = _allocation_for(run, critical.id)
        assert critical_alloc.feasible is True
        assert critical_alloc.allocated_power_kw == 4.0
        assert "solar" in critical_alloc.reason.lower()
        assert "battery" in critical_alloc.reason.lower()

        battery_alloc = _allocation_for(run, battery.id)
        assert battery_alloc.action == AllocationAction.DISCHARGE
        assert battery_alloc.allocated_power_kw == 2.0

    def test_infeasible_critical_demand_is_reported_not_hidden(self):
        battery = battery_asset(soc_percent=30.0, max_discharge_kw=5.0)
        critical = critical_load_asset(max_power_kw=8.0)
        grid = grid_asset(available=False, operating_state=OperatingState.OFFLINE)

        context = CoordinationContext(
            assets=[battery, critical, grid],
            intents=[
                minimum_reserve_intent(battery.id, min_soc_percent=30.0),
                minimum_supply_intent(critical.id, min_power_kw=8.0),
            ],
            trigger_reason=TriggerReason.GRID_OUTAGE,
            now=NOW,
        )

        run = run_coordination(context)

        critical_alloc = _allocation_for(run, critical.id)
        assert critical_alloc.feasible is False
        assert critical_alloc.allocated_power_kw == 0.0
        assert "no further supply available" in critical_alloc.reason.lower()
        assert run.summary is not None
        assert "could not be fully satisfied" in run.summary

    def test_critical_load_takes_precedence_over_flexible_demand(self):
        solar = solar_asset(generating_kw=3.0)
        critical = critical_load_asset(max_power_kw=3.0)
        flexible = flexible_load_asset(max_power_kw=3.0)
        grid = grid_asset(available=False, operating_state=OperatingState.OFFLINE)

        context = CoordinationContext(
            assets=[solar, critical, flexible, grid],
            intents=[
                minimum_supply_intent(critical.id, min_power_kw=3.0),
                deferrable_intent(flexible.id),
            ],
            trigger_reason=TriggerReason.GRID_OUTAGE,
            now=NOW,
        )

        run = run_coordination(context)

        critical_alloc = _allocation_for(run, critical.id)
        flexible_alloc = _allocation_for(run, flexible.id)
        assert critical_alloc.feasible is True
        assert critical_alloc.allocated_power_kw == 3.0
        assert flexible_alloc.action == AllocationAction.DEFER
        assert flexible_alloc.allocated_power_kw == 0.0
