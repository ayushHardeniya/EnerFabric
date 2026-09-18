"""SQLAlchemy ORM models for the core persisted domain data.

These mirror the Pydantic domain model (``app.domain``) closely — one
table per persisted concept, columns matching domain fields — rather
than introducing a second, incompatible schema. ``app/db/repository.py``
is the only place that converts between an ORM row and its domain
model; nothing else in the application should import from this module
directly.

``JSON`` (not the Postgres-specific ``JSONB``) is used for the two
free-form fields (``grid_snapshot``, ``constraints_considered``) so the
exact same models work against both PostgreSQL (real/dev use) and
SQLite (isolated test databases — see ``tests/api/conftest.py``).
"""

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AssetModel(Base):
    __tablename__ = "assets"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False, index=True)

    capabilities: Mapped[list["CapabilityModel"]] = relationship(
        back_populates="asset", cascade="all, delete-orphan"
    )
    telemetry: Mapped[list["TelemetryModel"]] = relationship(
        back_populates="asset", cascade="all, delete-orphan"
    )
    intents: Mapped[list["IntentModel"]] = relationship(
        back_populates="asset", cascade="all, delete-orphan"
    )


class CapabilityModel(Base):
    __tablename__ = "capabilities"
    __table_args__ = (UniqueConstraint("asset_id", "type", name="uq_capability_asset_type"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[str] = mapped_column(
        ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String, nullable=False)
    max_power_kw: Mapped[float] = mapped_column(Float, nullable=False)
    min_power_kw: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    capacity_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)

    asset: Mapped[AssetModel] = relationship(back_populates="capabilities")


class TelemetryModel(Base):
    __tablename__ = "telemetry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[str] = mapped_column(
        ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    power_kw: Mapped[float] = mapped_column(Float, nullable=False)
    energy_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    soc_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    operating_state: Mapped[str] = mapped_column(String, nullable=False)

    asset: Mapped[AssetModel] = relationship(back_populates="telemetry")


class IntentModel(Base):
    __tablename__ = "intents"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    asset_id: Mapped[str] = mapped_column(
        ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Type-specific fields — nullable, populated according to `type`.
    target_soc_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    min_soc_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    min_power_kw: Mapped[float | None] = mapped_column(Float, nullable=True)
    window_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    window_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    asset: Mapped[AssetModel] = relationship(back_populates="intents")


class PolicyModel(Base):
    __tablename__ = "policies"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    description: Mapped[str] = mapped_column(String, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    threshold_kw: Mapped[float | None] = mapped_column(Float, nullable=True)
    threshold_percent: Mapped[float | None] = mapped_column(Float, nullable=True)


class CoordinationRunModel(Base):
    __tablename__ = "coordination_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    trigger_reason: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    grid_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    summary: Mapped[str | None] = mapped_column(String, nullable=True)

    allocations: Mapped[list["AllocationModel"]] = relationship(
        back_populates="coordination_run", cascade="all, delete-orphan"
    )
    impact: Mapped["ImpactModel | None"] = relationship(
        back_populates="coordination_run", cascade="all, delete-orphan", uselist=False
    )


class AllocationModel(Base):
    __tablename__ = "allocations"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    coordination_run_id: Mapped[str] = mapped_column(
        ForeignKey("coordination_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    asset_id: Mapped[str] = mapped_column(
        ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action: Mapped[str] = mapped_column(String, nullable=False)
    allocated_power_kw: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_soc_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    feasible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    reason: Mapped[str] = mapped_column(String, nullable=False)
    source_intent_id: Mapped[str | None] = mapped_column(String, nullable=True)
    constraints_considered: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    # Explicit insertion-order marker: the engine decides allocations in a
    # meaningful precedence order (critical loads first, grid last), and a
    # UUID primary key carries no ordering, so this is set from
    # ``enumerate(run.allocations)`` on save to preserve that order on read.
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    coordination_run: Mapped[CoordinationRunModel] = relationship(back_populates="allocations")


class ImpactModel(Base):
    __tablename__ = "impacts"

    coordination_run_id: Mapped[str] = mapped_column(
        ForeignKey("coordination_runs.id", ondelete="CASCADE"), primary_key=True
    )
    grid_import_reduction_kw: Mapped[float | None] = mapped_column(Float, nullable=True)
    renewable_utilization_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    peak_demand_reduction_kw: Mapped[float | None] = mapped_column(Float, nullable=True)
    curtailed_energy_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    critical_load_served_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    battery_reserve_maintained: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    coordination_run: Mapped[CoordinationRunModel] = relationship(back_populates="impact")
