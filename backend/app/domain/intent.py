"""Intent: what an asset needs or prefers — as opposed to Capability
(what it can do) or Telemetry (what it is doing).

Modeled as a discriminated union of small, purpose-built subclasses
rather than one class with a bag of optional fields. Each subclass
only carries the fields that are actually required for its shape, so
validation stays precise (e.g. a deadline-based intent cannot be
created without a deadline). New intent shapes are added as a new
IntentType + subclass, without touching existing ones — satisfying the
requirement that new intent types not force a domain-wide rewrite.
"""

from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import uuid4

from pydantic import AwareDatetime, Field, model_validator

from app.domain.base import DomainModel
from app.domain.enums import IntentType, Priority


class IntentBase(DomainModel):
    id: str = Field(default_factory=lambda: str(uuid4()), min_length=1)
    asset_id: str = Field(min_length=1)
    priority: Priority = Priority.MEDIUM
    description: str = Field(min_length=1)
    created_at: AwareDatetime = Field(default_factory=lambda: datetime.now(UTC))


class TargetSocByDeadlineIntent(IntentBase):
    """e.g. EV: "Reach 80% SOC before 07:00"."""

    type: Literal[IntentType.TARGET_SOC_BY_DEADLINE] = IntentType.TARGET_SOC_BY_DEADLINE
    target_soc_percent: float = Field(ge=0, le=100)
    deadline: AwareDatetime


class MinimumReserveIntent(IntentBase):
    """e.g. Battery: "Maintain at least 30% reserve"."""

    type: Literal[IntentType.MINIMUM_RESERVE] = IntentType.MINIMUM_RESERVE
    min_soc_percent: float = Field(ge=0, le=100)


class MinimumSupplyIntent(IntentBase):
    """e.g. Critical load: "Maintain minimum supply"."""

    type: Literal[IntentType.MINIMUM_SUPPLY] = IntentType.MINIMUM_SUPPLY
    min_power_kw: float = Field(ge=0)


class DeferrableIntent(IntentBase):
    """e.g. Flexible load: "May be deferred", optionally within a window."""

    type: Literal[IntentType.DEFERRABLE] = IntentType.DEFERRABLE
    window_start: AwareDatetime | None = None
    window_end: AwareDatetime | None = None

    @model_validator(mode="after")
    def _check_window(self) -> "DeferrableIntent":
        if (
            self.window_start is not None
            and self.window_end is not None
            and self.window_start >= self.window_end
        ):
            raise ValueError("window_start must be before window_end")
        return self


class PreferRenewableIntent(IntentBase):
    """e.g. Site: "Prefer renewable energy". Typically attached to a
    SITE-typed asset rather than an individual DER.
    """

    type: Literal[IntentType.PREFER_RENEWABLE] = IntentType.PREFER_RENEWABLE


Intent = Annotated[
    TargetSocByDeadlineIntent
    | MinimumReserveIntent
    | MinimumSupplyIntent
    | DeferrableIntent
    | PreferRenewableIntent,
    Field(discriminator="type"),
]
