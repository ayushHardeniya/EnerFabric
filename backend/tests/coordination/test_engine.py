from app.coordination import CoordinationContext, run_coordination
from app.domain import (
    AllocationAction,
    CoordinationRunStatus,
    OperatingState,
    PolicyType,
    Priority,
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


class TestBasicFeasibleAllocation:
    def test_solar_surplus_charges_ev(self):
        solar = solar_asset(generating_kw=6.0)
        ev = ev_charger_asset(max_power_kw=5.0)
        context = CoordinationContext(
            assets=[solar, ev],
            intents=[target_soc_intent(ev.id)],
            trigger_reason=TriggerReason.SOLAR_SURPLUS,
            now=NOW,
        )
        run = run_coordination(context)
        assert run.status == CoordinationRunStatus.COMPLETED
        ev_alloc = _allocation_for(run, ev.id)
        assert ev_alloc.action == AllocationAction.CHARGE
        assert ev_alloc.allocated_power_kw == 5.0
        assert ev_alloc.feasible is True
        assert "solar" in ev_alloc.reason.lower()


class TestCapabilityLimits:
    def test_ev_charging_never_exceeds_capability_max(self):
        solar = solar_asset(generating_kw=50.0)
        ev = ev_charger_asset(max_power_kw=7.0)
        context = CoordinationContext(
            assets=[solar, ev], intents=[target_soc_intent(ev.id)], now=NOW
        )
        run = run_coordination(context)
        ev_alloc = _allocation_for(run, ev.id)
        assert ev_alloc.allocated_power_kw == 7.0

    def test_flexible_load_never_exceeds_capability_max(self):
        solar = solar_asset(generating_kw=50.0)
        load = flexible_load_asset(max_power_kw=3.0)
        context = CoordinationContext(assets=[solar, load], now=NOW)
        run = run_coordination(context)
        alloc = _allocation_for(run, load.id)
        assert alloc.allocated_power_kw == 3.0


class TestUnavailableAssets:
    def test_offline_solar_contributes_no_generation(self):
        solar = solar_asset(operating_state=OperatingState.OFFLINE)
        context = CoordinationContext(assets=[solar], now=NOW)
        run = run_coordination(context)
        alloc = _allocation_for(run, solar.id)
        assert alloc.action == AllocationAction.HOLD
        assert alloc.allocated_power_kw == 0.0

    def test_unavailable_ev_charger_is_held(self):
        solar = solar_asset(generating_kw=10.0)
        ev = ev_charger_asset(available=False)
        context = CoordinationContext(
            assets=[solar, ev], intents=[target_soc_intent(ev.id)], now=NOW
        )
        run = run_coordination(context)
        alloc = _allocation_for(run, ev.id)
        assert alloc.action == AllocationAction.HOLD
        assert alloc.feasible is False
        assert "unavailable" in alloc.reason.lower()


class TestBatteryReserveProtection:
    def test_battery_at_reserve_floor_does_not_discharge(self):
        battery = battery_asset(soc_percent=30.0)
        critical = critical_load_asset()
        context = CoordinationContext(
            assets=[battery, critical],
            intents=[
                minimum_reserve_intent(battery.id, min_soc_percent=30.0),
                minimum_supply_intent(critical.id, min_power_kw=2.0),
            ],
            now=NOW,
        )
        run = run_coordination(context)
        battery_alloc = _allocation_for(run, battery.id)
        assert battery_alloc.action == AllocationAction.HOLD
        assert battery_alloc.feasible is False
        assert "reserve" in battery_alloc.reason.lower()

    def test_battery_above_reserve_may_discharge_for_critical_load(self):
        battery = battery_asset(soc_percent=80.0, max_discharge_kw=5.0)
        critical = critical_load_asset(max_power_kw=3.0)
        context = CoordinationContext(
            assets=[battery, critical],
            intents=[
                minimum_reserve_intent(battery.id, min_soc_percent=30.0),
                minimum_supply_intent(critical.id, min_power_kw=3.0),
            ],
            now=NOW,
        )
        run = run_coordination(context)
        battery_alloc = _allocation_for(run, battery.id)
        assert battery_alloc.action == AllocationAction.DISCHARGE
        assert battery_alloc.allocated_power_kw == 3.0
        assert battery_alloc.feasible is True

    def test_battery_reserve_respected_via_system_policy_fallback(self):
        battery = battery_asset(soc_percent=25.0)
        critical = critical_load_asset()
        context = CoordinationContext(
            assets=[battery, critical],
            intents=[minimum_supply_intent(critical.id, min_power_kw=2.0)],
            policies=[policy(PolicyType.MAINTAIN_BATTERY_RESERVE, threshold_percent=30)],
            now=NOW,
        )
        run = run_coordination(context)
        battery_alloc = _allocation_for(run, battery.id)
        assert battery_alloc.action == AllocationAction.HOLD
        assert battery_alloc.feasible is False
        assert "reserve" in battery_alloc.reason.lower()


class TestGridImportLimit:
    def test_flexible_load_deferred_when_grid_limit_reached(self):
        grid = grid_asset()
        load = flexible_load_asset(max_power_kw=5.0)
        context = CoordinationContext(
            assets=[grid, load],
            intents=[deferrable_intent(load.id)],
            policies=[policy(PolicyType.LIMIT_GRID_IMPORT, threshold_kw=0.0)],
            now=NOW,
        )
        run = run_coordination(context)
        alloc = _allocation_for(run, load.id)
        assert alloc.action == AllocationAction.DEFER
        assert "grid import limit" in alloc.reason.lower()

    def test_flexible_load_runs_within_grid_budget(self):
        grid = grid_asset()
        load = flexible_load_asset(max_power_kw=3.0)
        context = CoordinationContext(
            assets=[grid, load],
            intents=[deferrable_intent(load.id)],
            policies=[policy(PolicyType.LIMIT_GRID_IMPORT, threshold_kw=10.0)],
            now=NOW,
        )
        run = run_coordination(context)
        alloc = _allocation_for(run, load.id)
        assert alloc.action == AllocationAction.CONSUME
        assert alloc.allocated_power_kw == 3.0

    def test_grid_allocation_reports_infeasible_when_critical_load_forces_overrun(self):
        grid = grid_asset()
        critical = critical_load_asset(max_power_kw=10.0)
        context = CoordinationContext(
            assets=[grid, critical],
            intents=[minimum_supply_intent(critical.id, min_power_kw=10.0)],
            policies=[policy(PolicyType.LIMIT_GRID_IMPORT, threshold_kw=2.0)],
            now=NOW,
        )
        run = run_coordination(context)
        grid_alloc = _allocation_for(run, grid.id)
        assert grid_alloc.allocated_power_kw == 10.0
        assert grid_alloc.feasible is False
        assert "exceeds" in grid_alloc.reason.lower()
        critical_alloc = _allocation_for(run, critical.id)
        assert critical_alloc.feasible is True


class TestCriticalLoadPriority:
    def test_critical_load_served_before_flexible_load(self):
        solar = solar_asset(generating_kw=3.0)
        critical = critical_load_asset(max_power_kw=3.0)
        flexible = flexible_load_asset(max_power_kw=3.0)
        context = CoordinationContext(
            assets=[solar, critical, flexible],
            intents=[
                minimum_supply_intent(critical.id, min_power_kw=3.0),
                deferrable_intent(flexible.id),
            ],
            now=NOW,
        )
        run = run_coordination(context)
        critical_alloc = _allocation_for(run, critical.id)
        flexible_alloc = _allocation_for(run, flexible.id)
        assert critical_alloc.allocated_power_kw == 3.0
        assert critical_alloc.feasible is True
        assert flexible_alloc.action == AllocationAction.DEFER

    def test_critical_load_infeasible_is_reported_explicitly(self):
        critical = critical_load_asset(max_power_kw=5.0)
        context = CoordinationContext(
            assets=[critical],
            intents=[minimum_supply_intent(critical.id, min_power_kw=5.0)],
            trigger_reason=TriggerReason.GRID_OUTAGE,
            now=NOW,
        )
        run = run_coordination(context)
        alloc = _allocation_for(run, critical.id)
        assert alloc.feasible is False
        assert alloc.allocated_power_kw == 0.0
        assert "0.00 kW of the required 5.00 kW" in alloc.reason


class TestRenewablePreference:
    def test_solar_used_before_grid_for_ev_charging(self):
        solar = solar_asset(generating_kw=4.0)
        grid = grid_asset()
        ev = ev_charger_asset(max_power_kw=7.0)
        context = CoordinationContext(
            assets=[solar, grid, ev], intents=[target_soc_intent(ev.id)], now=NOW
        )
        run = run_coordination(context)
        alloc = _allocation_for(run, ev.id)
        assert alloc.allocated_power_kw == 7.0
        assert "4.00 kW solar" in alloc.reason
        assert "3.00 kW grid" in alloc.reason

    def test_battery_charges_from_solar_surplus(self):
        solar = solar_asset(generating_kw=4.0)
        battery = battery_asset(soc_percent=50.0, max_charge_kw=5.0)
        context = CoordinationContext(assets=[solar, battery], now=NOW)
        run = run_coordination(context)
        battery_alloc = _allocation_for(run, battery.id)
        assert battery_alloc.action == AllocationAction.CHARGE
        assert battery_alloc.allocated_power_kw == 4.0


class TestIntentPriorityAndConflicts:
    def test_higher_priority_ev_charger_served_first_when_supply_limited(self):
        solar = solar_asset(generating_kw=5.0)
        high_ev = ev_charger_asset("ev-high", max_power_kw=5.0)
        low_ev = ev_charger_asset("ev-low", max_power_kw=5.0)
        context = CoordinationContext(
            assets=[solar, high_ev, low_ev],
            intents=[
                target_soc_intent(high_ev.id, priority=Priority.HIGH),
                target_soc_intent(low_ev.id, priority=Priority.LOW),
            ],
            now=NOW,
        )
        run = run_coordination(context)
        high_alloc = _allocation_for(run, high_ev.id)
        low_alloc = _allocation_for(run, low_ev.id)
        assert high_alloc.allocated_power_kw == 5.0
        assert low_alloc.allocated_power_kw == 0.0
        assert low_alloc.feasible is False

    def test_conflicting_ev_demand_without_grid_defers_lower_priority(self):
        solar = solar_asset(generating_kw=6.0)
        first = ev_charger_asset("ev-a", max_power_kw=6.0)
        second = ev_charger_asset("ev-b", max_power_kw=6.0)
        context = CoordinationContext(
            assets=[solar, first, second],
            intents=[
                target_soc_intent(first.id, priority=Priority.MEDIUM),
                target_soc_intent(second.id, priority=Priority.MEDIUM),
            ],
            now=NOW,
        )
        run = run_coordination(context)
        first_alloc = _allocation_for(run, first.id)
        second_alloc = _allocation_for(run, second.id)
        assert first_alloc.allocated_power_kw == 6.0
        assert second_alloc.allocated_power_kw == 0.0
        assert second_alloc.action == AllocationAction.HOLD


class TestInfeasibleRequests:
    def test_no_sources_available_marks_critical_load_infeasible(self):
        critical = critical_load_asset(max_power_kw=2.0, operating_state=OperatingState.ONLINE)
        context = CoordinationContext(
            assets=[critical],
            intents=[minimum_supply_intent(critical.id, min_power_kw=2.0)],
            now=NOW,
        )
        run = run_coordination(context)
        alloc = _allocation_for(run, critical.id)
        assert alloc.feasible is False
        assert run.summary is not None
        assert "could not be fully satisfied" in run.summary

    def test_run_summary_reports_success_when_all_feasible(self):
        solar = solar_asset(generating_kw=5.0)
        ev = ev_charger_asset(max_power_kw=5.0)
        context = CoordinationContext(
            assets=[solar, ev], intents=[target_soc_intent(ev.id)], now=NOW
        )
        run = run_coordination(context)
        assert all(a.feasible for a in run.allocations)
        assert "all requirements were met" in run.summary


class TestDeterminism:
    def test_repeated_execution_produces_identical_decisions(self):
        solar = solar_asset(generating_kw=6.0)
        battery = battery_asset(soc_percent=50.0)
        ev = ev_charger_asset(max_power_kw=5.0)
        critical = critical_load_asset(max_power_kw=2.0)
        flexible = flexible_load_asset(max_power_kw=3.0)
        grid = grid_asset()
        intents = [
            target_soc_intent(ev.id),
            minimum_reserve_intent(battery.id, min_soc_percent=30.0),
            minimum_supply_intent(critical.id, min_power_kw=2.0),
            deferrable_intent(flexible.id),
        ]
        policies = [policy(PolicyType.LIMIT_GRID_IMPORT, threshold_kw=10.0)]

        def build_context():
            return CoordinationContext(
                assets=[solar, battery, ev, critical, flexible, grid],
                intents=intents,
                policies=policies,
                trigger_reason=TriggerReason.PEAK_DEMAND,
                now=NOW,
            )

        first = run_coordination(build_context())
        second = run_coordination(build_context())

        first_summary = [
            (a.asset_id, a.action, a.allocated_power_kw, a.feasible, a.reason)
            for a in first.allocations
        ]
        second_summary = [
            (a.asset_id, a.action, a.allocated_power_kw, a.feasible, a.reason)
            for a in second.allocations
        ]
        assert first_summary == second_summary
        assert first.summary == second.summary

    def test_asset_input_order_does_not_change_decision(self):
        solar = solar_asset(generating_kw=4.0)
        ev = ev_charger_asset(max_power_kw=4.0)
        intents = [target_soc_intent(ev.id)]

        forward = run_coordination(
            CoordinationContext(assets=[solar, ev], intents=intents, now=NOW)
        )
        reversed_ = run_coordination(
            CoordinationContext(assets=[ev, solar], intents=intents, now=NOW)
        )
        assert _allocation_for(forward, ev.id).allocated_power_kw == (
            _allocation_for(reversed_, ev.id).allocated_power_kw
        )


class TestExplanationGeneration:
    def test_every_allocation_has_non_blank_reason(self):
        solar = solar_asset(generating_kw=6.0)
        battery = battery_asset(soc_percent=50.0)
        ev = ev_charger_asset(max_power_kw=5.0)
        critical = critical_load_asset(max_power_kw=2.0)
        flexible = flexible_load_asset(max_power_kw=3.0)
        grid = grid_asset()
        context = CoordinationContext(
            assets=[solar, battery, ev, critical, flexible, grid],
            intents=[
                target_soc_intent(ev.id),
                minimum_reserve_intent(battery.id),
                minimum_supply_intent(critical.id),
                deferrable_intent(flexible.id),
            ],
            now=NOW,
        )
        run = run_coordination(context)
        assert run.allocations
        for allocation in run.allocations:
            assert allocation.reason.strip() != ""
            assert allocation.constraints_considered is not None

    def test_ev_charging_reason_explains_power_selection(self):
        solar = solar_asset(generating_kw=3.5)
        ev = ev_charger_asset(max_power_kw=3.5)
        context = CoordinationContext(
            assets=[solar, ev], intents=[target_soc_intent(ev.id)], now=NOW
        )
        run = run_coordination(context)
        alloc = _allocation_for(run, ev.id)
        assert "3.50 kW" in alloc.reason
        assert "solar" in alloc.reason.lower()
