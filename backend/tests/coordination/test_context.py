from app.coordination.context import CoordinationContext
from app.domain import AssetType, PolicyType, TriggerReason
from tests.coordination.factories import (
    NOW,
    battery_asset,
    minimum_reserve_intent,
    policy,
    solar_asset,
)


def test_asset_lookup_by_id():
    solar = solar_asset("solar-1")
    context = CoordinationContext(assets=[solar])
    assert context.asset("solar-1") is solar
    assert context.asset("missing") is None


def test_assets_of_type_sorted_by_id():
    b = battery_asset("battery-b")
    a = battery_asset("battery-a")
    context = CoordinationContext(assets=[b, a])
    assert [x.id for x in context.assets_of_type(AssetType.BATTERY)] == ["battery-a", "battery-b"]
    assert context.assets_of_type(AssetType.SOLAR) == []


def test_intents_for_asset_filters_by_asset_id():
    intent = minimum_reserve_intent("battery-1")
    other = minimum_reserve_intent("battery-2")
    context = CoordinationContext(assets=[], intents=[intent, other])
    assert context.intents_for_asset("battery-1") == [intent]


def test_enabled_policies_of_type_excludes_disabled():
    enabled = policy(PolicyType.LIMIT_GRID_IMPORT, threshold_kw=10, enabled=True)
    disabled = policy(PolicyType.LIMIT_GRID_IMPORT, threshold_kw=5, enabled=False)
    context = CoordinationContext(assets=[], policies=[enabled, disabled])
    assert context.enabled_policies_of_type(PolicyType.LIMIT_GRID_IMPORT) == [enabled]


def test_defaults():
    context = CoordinationContext(assets=[])
    assert context.intents == []
    assert context.policies == []
    assert context.trigger_reason == TriggerReason.MANUAL
    assert context.now is not None


def test_now_is_settable_for_determinism():
    context = CoordinationContext(assets=[], now=NOW)
    assert context.now == NOW
