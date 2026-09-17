"""Core domain model: Asset, Capability, Telemetry, Intent, Policy,
CoordinationRun, Allocation, Impact.

Framework-independent by design: no FastAPI, SQLAlchemy, MQTT, or
frontend concerns belong here. Later adapters translate between this
model and infrastructure-specific representations.
"""

from app.domain.asset import Asset, Capability
from app.domain.coordination import Allocation, CoordinationRun
from app.domain.enums import (
    AllocationAction,
    AssetType,
    CapabilityType,
    CoordinationRunStatus,
    IntentType,
    OperatingState,
    PolicyType,
    Priority,
    TriggerReason,
)
from app.domain.impact import Impact
from app.domain.intent import (
    DeferrableIntent,
    Intent,
    IntentBase,
    MinimumReserveIntent,
    MinimumSupplyIntent,
    PreferRenewableIntent,
    TargetSocByDeadlineIntent,
)
from app.domain.policy import Policy
from app.domain.telemetry import Telemetry

__all__ = [
    "Allocation",
    "AllocationAction",
    "Asset",
    "AssetType",
    "Capability",
    "CapabilityType",
    "CoordinationRun",
    "CoordinationRunStatus",
    "DeferrableIntent",
    "Impact",
    "Intent",
    "IntentBase",
    "IntentType",
    "MinimumReserveIntent",
    "MinimumSupplyIntent",
    "OperatingState",
    "Policy",
    "PolicyType",
    "PreferRenewableIntent",
    "Priority",
    "TargetSocByDeadlineIntent",
    "Telemetry",
    "TriggerReason",
]
