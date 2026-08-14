"""Telemetry: what an asset is currently doing.

Distinct from Intent (what an asset needs/prefers) and from Asset
identity/configuration (see asset.py).
"""

from pydantic import AwareDatetime, Field

from app.domain.base import DomainModel
from app.domain.enums import OperatingState


class Telemetry(DomainModel):
    """A single observed snapshot of an asset's state.

    Sign convention for ``power_kw`` (applies uniformly to every asset,
    including the Grid asset): positive means the asset is a net
    source of power onto the site's internal bus (generating or
    discharging); negative means it is a net sink (consuming or
    charging). For the Grid asset specifically, positive therefore
    means the site is importing from the grid, and negative means the
    site is exporting to it.
    """

    asset_id: str = Field(min_length=1)
    timestamp: AwareDatetime
    power_kw: float
    energy_kwh: float | None = Field(default=None, ge=0)
    soc_percent: float | None = Field(default=None, ge=0, le=100)
    available: bool = True
    operating_state: OperatingState = OperatingState.ONLINE
