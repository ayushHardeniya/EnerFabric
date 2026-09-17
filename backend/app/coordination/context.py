"""CoordinationContext: the coordination engine's input snapshot.

Bundles current assets (each carrying its own ``latest_telemetry``),
active intents, system policies, and what triggered this coordination
cycle. This is the engine's own input type — not a domain persistence
model (see ``app.domain.coordination`` for ``CoordinationRun``) and not
tied to any transport (API, MQTT, tests all build one the same way).

Framework-independent: no FastAPI/DB/MQTT concerns, no I/O. Frozen so a
context can't be mutated mid-decision, keeping the engine's "same input
always produces the same output" guarantee easy to reason about.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.domain import Asset, AssetType, Intent, Policy, PolicyType, TriggerReason


@dataclass(frozen=True)
class CoordinationContext:
    assets: list[Asset]
    intents: list[Intent] = field(default_factory=list)
    policies: list[Policy] = field(default_factory=list)
    trigger_reason: TriggerReason = TriggerReason.MANUAL
    now: datetime = field(default_factory=lambda: datetime.now(UTC))

    def asset(self, asset_id: str) -> Asset | None:
        return next((a for a in self.assets if a.id == asset_id), None)

    def assets_of_type(self, asset_type: AssetType) -> list[Asset]:
        """Assets of the given type, sorted by id for deterministic processing order."""
        return sorted((a for a in self.assets if a.type == asset_type), key=lambda a: a.id)

    def intents_for_asset(self, asset_id: str) -> list[Intent]:
        return [i for i in self.intents if i.asset_id == asset_id]

    def enabled_policies_of_type(self, policy_type: PolicyType) -> list[Policy]:
        return [p for p in self.policies if p.type == policy_type and p.enabled]
