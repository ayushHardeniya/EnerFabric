import pytest
from pydantic import ValidationError

from app.domain import Impact


class TestImpact:
    def test_required_fields(self):
        with pytest.raises(ValidationError):
            Impact()  # missing coordination_run_id

    def test_all_metrics_optional(self):
        impact = Impact(coordination_run_id="run-1")
        assert impact.grid_import_reduction_kw is None
        assert impact.renewable_utilization_percent is None
        assert impact.battery_reserve_maintained is None

    def test_renewable_utilization_percent_boundaries(self):
        Impact(coordination_run_id="run-1", renewable_utilization_percent=0)
        Impact(coordination_run_id="run-1", renewable_utilization_percent=100)
        with pytest.raises(ValidationError):
            Impact(coordination_run_id="run-1", renewable_utilization_percent=101)

    def test_curtailed_energy_must_be_non_negative(self):
        with pytest.raises(ValidationError):
            Impact(coordination_run_id="run-1", curtailed_energy_kwh=-1)

    def test_representative_full_impact(self):
        impact = Impact(
            coordination_run_id="run-1",
            grid_import_reduction_kw=5.0,
            renewable_utilization_percent=85.0,
            peak_demand_reduction_kw=2.0,
            curtailed_energy_kwh=0.0,
            critical_load_served_percent=100.0,
            battery_reserve_maintained=True,
        )
        assert impact.battery_reserve_maintained is True

    def test_serialization_roundtrip(self):
        impact = Impact(coordination_run_id="run-1", grid_import_reduction_kw=5.0)
        restored = Impact.model_validate(impact.model_dump(mode="json"))
        assert restored == impact
