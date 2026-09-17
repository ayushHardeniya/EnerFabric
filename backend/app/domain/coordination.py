"""CoordinationRun and Allocation: the domain representation of one
orchestration decision cycle and the per-asset decisions within it.

This module defines data only — no orchestration algorithm. The
coordination engine that populates these models is implemented in
Milestone 2.
"""

from datetime import UTC, datetime
from uuid import uuid4

from pydantic import AwareDatetime, Field

from app.domain.base import DomainModel
from app.domain.enums import AllocationAction, CoordinationRunStatus, TriggerReason
from app.domain.impact import Impact
from app.domain.telemetry import Telemetry


class Allocation(DomainModel):
    """What EnerFabric decided to do for one asset during a
    CoordinationRun, and why.

    ``allocated_power_kw`` is a non-negative magnitude — direction is
    conveyed by ``action`` (e.g. CHARGE vs DISCHARGE), unlike
    Telemetry.power_kw which is signed because it has no separate
    action field to carry direction.

    ``reason`` is required: every allocation must be explainable, not
    just decided — this is a core product property, not optional
    polish.
    """

    id: str = Field(default_factory=lambda: str(uuid4()), min_length=1)
    coordination_run_id: str = Field(min_length=1)
    asset_id: str = Field(min_length=1)
    action: AllocationAction
    allocated_power_kw: float | None = Field(default=None, ge=0)
    target_soc_percent: float | None = Field(default=None, ge=0, le=100)
    feasible: bool = True
    reason: str = Field(min_length=1)
    source_intent_id: str | None = None
    constraints_considered: list[str] = Field(default_factory=list)


class CoordinationRun(DomainModel):
    """One orchestration decision cycle: what triggered it, what was
    decided (its Allocations), and what resulted (its Impact).

    ``grid_snapshot`` reuses Telemetry (for the Grid asset) rather than
    a bespoke grid-state schema, keeping "relevant grid state" a
    reference to an existing model instead of a duplicated one.
    """

    id: str = Field(default_factory=lambda: str(uuid4()), min_length=1)
    triggered_at: AwareDatetime = Field(default_factory=lambda: datetime.now(UTC))
    trigger_reason: TriggerReason
    status: CoordinationRunStatus = CoordinationRunStatus.PENDING
    grid_snapshot: Telemetry | None = None
    allocations: list[Allocation] = Field(default_factory=list)
    impact: Impact | None = None
    summary: str | None = None
