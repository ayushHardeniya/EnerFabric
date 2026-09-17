from datetime import UTC, datetime, timedelta

import pytest
from pydantic import TypeAdapter, ValidationError

from app.domain import (
    DeferrableIntent,
    Intent,
    IntentType,
    MinimumReserveIntent,
    MinimumSupplyIntent,
    PreferRenewableIntent,
    Priority,
    TargetSocByDeadlineIntent,
)

intent_adapter = TypeAdapter(Intent)


class TestTargetSocByDeadlineIntent:
    """EV: "Reach 80% SOC before 07:00"."""

    def test_valid_creation(self):
        intent = TargetSocByDeadlineIntent(
            asset_id="ev-1",
            description="Reach 80% SOC before 07:00",
            target_soc_percent=80,
            deadline=datetime(2026, 8, 14, 7, 0, tzinfo=UTC),
            priority=Priority.MEDIUM,
        )
        assert intent.type is IntentType.TARGET_SOC_BY_DEADLINE

    def test_deadline_required(self):
        with pytest.raises(ValidationError):
            TargetSocByDeadlineIntent(
                asset_id="ev-1", description="Reach 80%", target_soc_percent=80
            )

    def test_deadline_must_be_timezone_aware(self):
        with pytest.raises(ValidationError):
            TargetSocByDeadlineIntent(
                asset_id="ev-1",
                description="Reach 80%",
                target_soc_percent=80,
                deadline=datetime(2026, 8, 14, 7, 0),
            )

    def test_target_soc_out_of_bounds_rejected(self):
        with pytest.raises(ValidationError):
            TargetSocByDeadlineIntent(
                asset_id="ev-1",
                description="Reach 150%",
                target_soc_percent=150,
                deadline=datetime(2026, 8, 14, 7, 0, tzinfo=UTC),
            )

    def test_priority_defaults_to_medium(self):
        intent = TargetSocByDeadlineIntent(
            asset_id="ev-1",
            description="Reach 80%",
            target_soc_percent=80,
            deadline=datetime(2026, 8, 14, 7, 0, tzinfo=UTC),
        )
        assert intent.priority is Priority.MEDIUM


class TestMinimumReserveIntent:
    """Battery: "Maintain at least 30% reserve"."""

    def test_valid_creation(self):
        intent = MinimumReserveIntent(
            asset_id="battery-1",
            description="Maintain at least 30% reserve",
            min_soc_percent=30,
            priority=Priority.HIGH,
        )
        assert intent.min_soc_percent == 30

    def test_min_soc_boundaries(self):
        MinimumReserveIntent(asset_id="battery-1", description="x", min_soc_percent=0)
        MinimumReserveIntent(asset_id="battery-1", description="x", min_soc_percent=100)
        with pytest.raises(ValidationError):
            MinimumReserveIntent(asset_id="battery-1", description="x", min_soc_percent=-1)
        with pytest.raises(ValidationError):
            MinimumReserveIntent(asset_id="battery-1", description="x", min_soc_percent=101)


class TestMinimumSupplyIntent:
    """Critical load: "Maintain minimum supply"."""

    def test_valid_creation(self):
        intent = MinimumSupplyIntent(
            asset_id="load-critical-1",
            description="Maintain minimum supply",
            min_power_kw=4.0,
            priority=Priority.CRITICAL,
        )
        assert intent.priority is Priority.CRITICAL

    def test_negative_power_rejected(self):
        with pytest.raises(ValidationError):
            MinimumSupplyIntent(
                asset_id="load-critical-1", description="x", min_power_kw=-1.0
            )


class TestDeferrableIntent:
    """Flexible load: "May be deferred"."""

    def test_valid_creation_without_window(self):
        intent = DeferrableIntent(asset_id="load-1", description="May be deferred")
        assert intent.window_start is None and intent.window_end is None

    def test_valid_creation_with_window(self):
        start = datetime(2026, 8, 13, 22, 0, tzinfo=UTC)
        end = start + timedelta(hours=6)
        intent = DeferrableIntent(
            asset_id="load-1",
            description="Deferrable overnight",
            window_start=start,
            window_end=end,
        )
        assert intent.window_end > intent.window_start

    def test_window_start_after_end_rejected(self):
        start = datetime(2026, 8, 13, 22, 0, tzinfo=UTC)
        with pytest.raises(ValidationError):
            DeferrableIntent(
                asset_id="load-1",
                description="x",
                window_start=start,
                window_end=start - timedelta(hours=1),
            )


class TestPreferRenewableIntent:
    """Site: "Prefer renewable energy"."""

    def test_valid_creation_on_site_asset(self):
        intent = PreferRenewableIntent(asset_id="site-1", description="Prefer renewable energy")
        assert intent.type is IntentType.PREFER_RENEWABLE


class TestIntentDiscriminatedUnion:
    def test_parses_to_correct_subclass_by_type(self):
        parsed = intent_adapter.validate_python(
            {
                "type": "minimum_reserve",
                "asset_id": "battery-1",
                "description": "Maintain at least 30% reserve",
                "min_soc_percent": 30,
            }
        )
        assert isinstance(parsed, MinimumReserveIntent)

    def test_invalid_type_discriminator_rejected(self):
        with pytest.raises(ValidationError):
            intent_adapter.validate_python(
                {"type": "not_a_real_intent_type", "asset_id": "x", "description": "x"}
            )

    def test_asset_id_required_across_all_intent_types(self):
        with pytest.raises(ValidationError):
            intent_adapter.validate_python(
                {
                    "type": "prefer_renewable",
                    "description": "Prefer renewable energy",
                }
            )
