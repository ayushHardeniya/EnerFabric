"""Asset: identity and configuration of a distributed energy resource
or system-level resource, plus what it is capable of (Capability).

Deliberately excludes observed state — see telemetry.py — and needs/
preferences — see intent.py. Asset only answers "what is this, and
what can it do", never "what is it doing right now" or "what does it
want".
"""

from uuid import uuid4

from pydantic import Field, model_validator

from app.domain.base import DomainModel
from app.domain.enums import AssetType, CapabilityType
from app.domain.telemetry import Telemetry


class Capability(DomainModel):
    """One thing an asset can physically/operationally do, with enough
    structure for the future coordination engine to check feasibility.

    ``capacity_kwh`` is the usable energy capacity relevant to
    storage-like capabilities (typically CHARGE/DISCHARGE); it is left
    optional and unconstrained to any particular CapabilityType since
    that is a soft convention, not a hard domain rule.
    """

    type: CapabilityType
    max_power_kw: float = Field(gt=0)
    min_power_kw: float = Field(default=0, ge=0)
    capacity_kwh: float | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def _check_power_bounds(self) -> "Capability":
        if self.min_power_kw > self.max_power_kw:
            raise ValueError("min_power_kw must not exceed max_power_kw")
        return self


class Asset(DomainModel):
    """A distributed energy resource or system-level resource (e.g. the
    overall site, or the grid connection) that EnerFabric can reason
    about and, later, orchestrate.

    ``latest_telemetry`` is a reference to the most recent observed
    snapshot, not a duplication of telemetry fields on Asset itself —
    identity/configuration and observed state stay clearly separated.
    """

    id: str = Field(default_factory=lambda: str(uuid4()), min_length=1)
    name: str = Field(min_length=1)
    type: AssetType
    capabilities: list[Capability] = Field(default_factory=list)
    latest_telemetry: Telemetry | None = None

    @model_validator(mode="after")
    def _check_consistency(self) -> "Asset":
        types_seen = [c.type for c in self.capabilities]
        if len(types_seen) != len(set(types_seen)):
            raise ValueError("an asset must not declare the same capability type twice")
        if self.latest_telemetry is not None and self.latest_telemetry.asset_id != self.id:
            raise ValueError("latest_telemetry.asset_id must match this asset's id")
        return self
