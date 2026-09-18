"""Request schemas that intentionally differ from the domain model shape.

Everywhere else (Telemetry, Intent, Policy), the domain model itself is
used directly as the request/response body — its own field defaults
(server-generated ``id``, etc.) and validation are already exactly what
the API needs, and a parallel *Create schema would just duplicate that
shape. Asset is the one exception: ``latest_telemetry`` must not be
client-settable at creation time (telemetry is posted separately), so
it gets a dedicated creation schema that omits it.
"""

from pydantic import Field

from app.domain.asset import Capability
from app.domain.base import DomainModel
from app.domain.enums import AssetType, TriggerReason


class AssetCreate(DomainModel):
    name: str = Field(min_length=1)
    type: AssetType
    capabilities: list[Capability] = Field(default_factory=list)


class CoordinationRunCreate(DomainModel):
    trigger_reason: TriggerReason
