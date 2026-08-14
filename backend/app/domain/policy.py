"""Policy: a system-level rule/preference that influences orchestration,
as distinct from Intent (a requirement/preference tied to one asset or
stakeholder).

Kept as a single model with a couple of clearly-named optional
threshold fields rather than a discriminated union like Intent: policy
types are few, each needs at most one simple numeric parameter, and
the union pattern would add indirection without adding precision here.
Revisit if policy variety grows enough to warrant it.
"""

from uuid import uuid4

from pydantic import Field

from app.domain.base import DomainModel
from app.domain.enums import PolicyType, Priority


class Policy(DomainModel):
    """A system-level rule. ``threshold_kw`` is used by
    LIMIT_GRID_IMPORT / REDUCE_PEAK_DEMAND; ``threshold_percent`` is
    used by MAINTAIN_BATTERY_RESERVE. Both are unused (left None) for
    boolean-shaped policies like PROTECT_CRITICAL_LOADS and
    PREFER_RENEWABLE_ENERGY.
    """

    id: str = Field(default_factory=lambda: str(uuid4()), min_length=1)
    type: PolicyType
    description: str = Field(min_length=1)
    priority: Priority = Priority.HIGH
    enabled: bool = True
    threshold_kw: float | None = Field(default=None, ge=0)
    threshold_percent: float | None = Field(default=None, ge=0, le=100)
