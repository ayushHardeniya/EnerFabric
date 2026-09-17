import pytest
from pydantic import ValidationError

from app.domain import Policy, PolicyType, Priority


class TestPolicy:
    def test_required_fields(self):
        with pytest.raises(ValidationError):
            Policy(type=PolicyType.PROTECT_CRITICAL_LOADS)  # missing description

    def test_invalid_policy_type_rejected(self):
        with pytest.raises(ValidationError):
            Policy(type="do_whatever", description="x")

    def test_enabled_defaults_true(self):
        policy = Policy(
            type=PolicyType.PROTECT_CRITICAL_LOADS, description="Protect critical loads"
        )
        assert policy.enabled is True

    def test_threshold_percent_boundaries(self):
        with pytest.raises(ValidationError):
            Policy(
                type=PolicyType.MAINTAIN_BATTERY_RESERVE,
                description="Maintain battery reserve",
                threshold_percent=101,
            )

    def test_threshold_kw_must_be_non_negative(self):
        with pytest.raises(ValidationError):
            Policy(
                type=PolicyType.LIMIT_GRID_IMPORT,
                description="Limit grid import",
                threshold_kw=-10,
            )

    # Representative examples for each canonical policy.

    def test_protect_critical_loads_example(self):
        policy = Policy(
            type=PolicyType.PROTECT_CRITICAL_LOADS,
            description="Protect critical loads",
            priority=Priority.CRITICAL,
        )
        assert policy.priority is Priority.CRITICAL

    def test_maintain_battery_reserve_example(self):
        policy = Policy(
            type=PolicyType.MAINTAIN_BATTERY_RESERVE,
            description="Maintain at least 20% battery reserve system-wide",
            threshold_percent=20,
        )
        assert policy.threshold_percent == 20

    def test_limit_grid_import_example(self):
        policy = Policy(
            type=PolicyType.LIMIT_GRID_IMPORT,
            description="Limit grid import to 50 kW",
            threshold_kw=50,
        )
        assert policy.threshold_kw == 50

    def test_prefer_renewable_energy_example(self):
        policy = Policy(
            type=PolicyType.PREFER_RENEWABLE_ENERGY,
            description="Prefer renewable energy across the site",
        )
        assert policy.type is PolicyType.PREFER_RENEWABLE_ENERGY

    def test_reduce_peak_demand_example(self):
        policy = Policy(
            type=PolicyType.REDUCE_PEAK_DEMAND,
            description="Reduce peak demand",
            threshold_kw=100,
        )
        assert policy.threshold_kw == 100

    def test_serialization_roundtrip(self):
        policy = Policy(
            type=PolicyType.LIMIT_GRID_IMPORT, description="Limit grid import", threshold_kw=50
        )
        restored = Policy.model_validate(policy.model_dump(mode="json"))
        assert restored == policy
