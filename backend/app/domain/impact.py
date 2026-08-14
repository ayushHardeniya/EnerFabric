"""Impact: measurable outcomes of a CoordinationRun.

All fields optional and independent — not every run affects every
metric, and this is a plain record, not the calculation engine that
will populate it in a later milestone.
"""

from pydantic import Field

from app.domain.base import DomainModel


class Impact(DomainModel):
    coordination_run_id: str = Field(min_length=1)
    grid_import_reduction_kw: float | None = None
    renewable_utilization_percent: float | None = Field(default=None, ge=0, le=100)
    peak_demand_reduction_kw: float | None = None
    curtailed_energy_kwh: float | None = Field(default=None, ge=0)
    critical_load_served_percent: float | None = Field(default=None, ge=0, le=100)
    battery_reserve_maintained: bool | None = None
