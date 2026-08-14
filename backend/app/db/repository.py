"""The only place that converts between ORM rows (``app.db.models``) and
the framework-independent domain model (``app.domain``).

Every function here takes/returns domain objects; callers (API routes)
never see an ORM row. This keeps the domain model the single source of
truth for validation and shape, and keeps SQLAlchemy an implementation
detail of persistence.
"""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.coordination.context import CoordinationContext
from app.db.errors import NotFoundError
from app.db.models import (
    AllocationModel,
    AssetModel,
    CapabilityModel,
    CoordinationRunModel,
    ImpactModel,
    IntentModel,
    PolicyModel,
    TelemetryModel,
)
from app.domain import (
    Allocation,
    AllocationAction,
    Asset,
    AssetType,
    Capability,
    CapabilityType,
    CoordinationRun,
    CoordinationRunStatus,
    DeferrableIntent,
    Impact,
    Intent,
    IntentType,
    MinimumReserveIntent,
    MinimumSupplyIntent,
    OperatingState,
    Policy,
    PolicyType,
    PreferRenewableIntent,
    Priority,
    TargetSocByDeadlineIntent,
    Telemetry,
    TriggerReason,
)


def _ensure_aware(dt: datetime) -> datetime:
    """SQLite has no native tz-aware timestamp type and hands back naive
    datetimes; PostgreSQL (TIMESTAMPTZ) already returns aware ones, so
    this is a no-op there. Domain models require ``AwareDatetime``.
    """
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


# ---------------------------------------------------------------------------
# Assets
# ---------------------------------------------------------------------------


def _asset_to_domain(row: AssetModel, latest_telemetry: Telemetry | None) -> Asset:
    return Asset(
        id=row.id,
        name=row.name,
        type=AssetType(row.type),
        capabilities=[
            Capability(
                type=CapabilityType(c.type),
                max_power_kw=c.max_power_kw,
                min_power_kw=c.min_power_kw,
                capacity_kwh=c.capacity_kwh,
            )
            for c in row.capabilities
        ],
        latest_telemetry=latest_telemetry,
    )


def _latest_telemetry_for_asset(db: Session, asset_id: str) -> Telemetry | None:
    row = db.execute(
        select(TelemetryModel)
        .where(TelemetryModel.asset_id == asset_id)
        .order_by(TelemetryModel.timestamp.desc())
        .limit(1)
    ).scalar_one_or_none()
    return _telemetry_to_domain(row) if row is not None else None


def create_asset(db: Session, asset: Asset) -> Asset:
    row = AssetModel(
        id=asset.id,
        name=asset.name,
        type=asset.type.value,
        capabilities=[
            CapabilityModel(
                type=c.type.value,
                max_power_kw=c.max_power_kw,
                min_power_kw=c.min_power_kw,
                capacity_kwh=c.capacity_kwh,
            )
            for c in asset.capabilities
        ],
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _asset_to_domain(row, latest_telemetry=None)


def get_asset(db: Session, asset_id: str) -> Asset | None:
    row = db.get(AssetModel, asset_id)
    if row is None:
        return None
    return _asset_to_domain(row, _latest_telemetry_for_asset(db, asset_id))


def list_assets(db: Session) -> list[Asset]:
    rows = db.execute(select(AssetModel).order_by(AssetModel.id)).scalars().all()
    return [_asset_to_domain(row, _latest_telemetry_for_asset(db, row.id)) for row in rows]


# ---------------------------------------------------------------------------
# Telemetry
# ---------------------------------------------------------------------------


def _telemetry_to_domain(row: TelemetryModel) -> Telemetry:
    return Telemetry(
        asset_id=row.asset_id,
        timestamp=_ensure_aware(row.timestamp),
        power_kw=row.power_kw,
        energy_kwh=row.energy_kwh,
        soc_percent=row.soc_percent,
        available=row.available,
        operating_state=OperatingState(row.operating_state),
    )


def create_telemetry(db: Session, telemetry: Telemetry) -> Telemetry:
    if db.get(AssetModel, telemetry.asset_id) is None:
        raise NotFoundError(f"asset '{telemetry.asset_id}' not found")
    row = TelemetryModel(
        asset_id=telemetry.asset_id,
        timestamp=telemetry.timestamp,
        power_kw=telemetry.power_kw,
        energy_kwh=telemetry.energy_kwh,
        soc_percent=telemetry.soc_percent,
        available=telemetry.available,
        operating_state=telemetry.operating_state.value,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _telemetry_to_domain(row)


def list_telemetry(db: Session, asset_id: str | None = None) -> list[Telemetry]:
    stmt = select(TelemetryModel).order_by(TelemetryModel.timestamp)
    if asset_id is not None:
        stmt = stmt.where(TelemetryModel.asset_id == asset_id)
    rows = db.execute(stmt).scalars().all()
    return [_telemetry_to_domain(row) for row in rows]


# ---------------------------------------------------------------------------
# Intents
# ---------------------------------------------------------------------------


def _intent_to_domain(row: IntentModel) -> Intent:
    common = {
        "id": row.id,
        "asset_id": row.asset_id,
        "priority": Priority(row.priority),
        "description": row.description,
        "created_at": _ensure_aware(row.created_at),
    }
    intent_type = IntentType(row.type)
    if intent_type == IntentType.TARGET_SOC_BY_DEADLINE:
        return TargetSocByDeadlineIntent(
            **common,
            target_soc_percent=row.target_soc_percent,
            deadline=_ensure_aware(row.deadline),
        )
    if intent_type == IntentType.MINIMUM_RESERVE:
        return MinimumReserveIntent(**common, min_soc_percent=row.min_soc_percent)
    if intent_type == IntentType.MINIMUM_SUPPLY:
        return MinimumSupplyIntent(**common, min_power_kw=row.min_power_kw)
    if intent_type == IntentType.DEFERRABLE:
        return DeferrableIntent(
            **common,
            window_start=_ensure_aware(row.window_start) if row.window_start else None,
            window_end=_ensure_aware(row.window_end) if row.window_end else None,
        )
    return PreferRenewableIntent(**common)


def create_intent(db: Session, intent: Intent) -> Intent:
    if db.get(AssetModel, intent.asset_id) is None:
        raise NotFoundError(f"asset '{intent.asset_id}' not found")
    row = IntentModel(
        id=intent.id,
        asset_id=intent.asset_id,
        type=intent.type.value,
        priority=intent.priority.value,
        description=intent.description,
        created_at=intent.created_at,
        target_soc_percent=getattr(intent, "target_soc_percent", None),
        deadline=getattr(intent, "deadline", None),
        min_soc_percent=getattr(intent, "min_soc_percent", None),
        min_power_kw=getattr(intent, "min_power_kw", None),
        window_start=getattr(intent, "window_start", None),
        window_end=getattr(intent, "window_end", None),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _intent_to_domain(row)


def list_intents(db: Session, asset_id: str | None = None) -> list[Intent]:
    stmt = select(IntentModel).order_by(IntentModel.created_at)
    if asset_id is not None:
        stmt = stmt.where(IntentModel.asset_id == asset_id)
    rows = db.execute(stmt).scalars().all()
    return [_intent_to_domain(row) for row in rows]


# ---------------------------------------------------------------------------
# Policies
# ---------------------------------------------------------------------------


def _policy_to_domain(row: PolicyModel) -> Policy:
    return Policy(
        id=row.id,
        type=PolicyType(row.type),
        description=row.description,
        priority=Priority(row.priority),
        enabled=row.enabled,
        threshold_kw=row.threshold_kw,
        threshold_percent=row.threshold_percent,
    )


def create_policy(db: Session, policy: Policy) -> Policy:
    row = PolicyModel(
        id=policy.id,
        type=policy.type.value,
        description=policy.description,
        priority=policy.priority.value,
        enabled=policy.enabled,
        threshold_kw=policy.threshold_kw,
        threshold_percent=policy.threshold_percent,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _policy_to_domain(row)


def list_policies(db: Session) -> list[Policy]:
    rows = db.execute(select(PolicyModel).order_by(PolicyModel.id)).scalars().all()
    return [_policy_to_domain(row) for row in rows]


# ---------------------------------------------------------------------------
# Coordination
# ---------------------------------------------------------------------------


def build_coordination_context(
    db: Session, trigger_reason: TriggerReason, now: datetime | None = None
) -> CoordinationContext:
    """Assemble the coordination engine's input snapshot from persisted
    state: every asset (with its capabilities and latest telemetry),
    every intent, and every policy. The engine itself filters by
    ``enabled``/relevance, so all rows are passed through unfiltered.
    """
    kwargs = {"now": now} if now is not None else {}
    return CoordinationContext(
        assets=list_assets(db),
        intents=list_intents(db),
        policies=list_policies(db),
        trigger_reason=trigger_reason,
        **kwargs,
    )


def _allocation_to_domain(row: AllocationModel) -> Allocation:
    return Allocation(
        id=row.id,
        coordination_run_id=row.coordination_run_id,
        asset_id=row.asset_id,
        action=AllocationAction(row.action),
        allocated_power_kw=row.allocated_power_kw,
        target_soc_percent=row.target_soc_percent,
        feasible=row.feasible,
        reason=row.reason,
        source_intent_id=row.source_intent_id,
        constraints_considered=list(row.constraints_considered or []),
    )


def _impact_to_domain(row: ImpactModel) -> Impact:
    return Impact(
        coordination_run_id=row.coordination_run_id,
        grid_import_reduction_kw=row.grid_import_reduction_kw,
        renewable_utilization_percent=row.renewable_utilization_percent,
        peak_demand_reduction_kw=row.peak_demand_reduction_kw,
        curtailed_energy_kwh=row.curtailed_energy_kwh,
        critical_load_served_percent=row.critical_load_served_percent,
        battery_reserve_maintained=row.battery_reserve_maintained,
    )


def _coordination_run_to_domain(row: CoordinationRunModel) -> CoordinationRun:
    ordered_allocations = sorted(row.allocations, key=lambda a: a.sequence_no)
    return CoordinationRun(
        id=row.id,
        triggered_at=_ensure_aware(row.triggered_at),
        trigger_reason=TriggerReason(row.trigger_reason),
        status=CoordinationRunStatus(row.status),
        grid_snapshot=Telemetry.model_validate(row.grid_snapshot) if row.grid_snapshot else None,
        allocations=[_allocation_to_domain(a) for a in ordered_allocations],
        impact=_impact_to_domain(row.impact) if row.impact else None,
        summary=row.summary,
    )


def save_coordination_run(db: Session, run: CoordinationRun) -> CoordinationRun:
    row = CoordinationRunModel(
        id=run.id,
        triggered_at=run.triggered_at,
        trigger_reason=run.trigger_reason.value,
        status=run.status.value,
        grid_snapshot=run.grid_snapshot.model_dump(mode="json") if run.grid_snapshot else None,
        summary=run.summary,
        allocations=[
            AllocationModel(
                id=a.id,
                asset_id=a.asset_id,
                action=a.action.value,
                allocated_power_kw=a.allocated_power_kw,
                target_soc_percent=a.target_soc_percent,
                feasible=a.feasible,
                reason=a.reason,
                source_intent_id=a.source_intent_id,
                constraints_considered=a.constraints_considered,
                sequence_no=i,
            )
            for i, a in enumerate(run.allocations)
        ],
    )
    if run.impact is not None:
        row.impact = ImpactModel(
            coordination_run_id=run.id,
            grid_import_reduction_kw=run.impact.grid_import_reduction_kw,
            renewable_utilization_percent=run.impact.renewable_utilization_percent,
            peak_demand_reduction_kw=run.impact.peak_demand_reduction_kw,
            curtailed_energy_kwh=run.impact.curtailed_energy_kwh,
            critical_load_served_percent=run.impact.critical_load_served_percent,
            battery_reserve_maintained=run.impact.battery_reserve_maintained,
        )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _coordination_run_to_domain(row)


def get_coordination_run(db: Session, run_id: str) -> CoordinationRun | None:
    row = db.get(CoordinationRunModel, run_id)
    if row is None:
        return None
    return _coordination_run_to_domain(row)
