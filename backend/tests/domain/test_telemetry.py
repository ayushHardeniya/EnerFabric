from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.domain import OperatingState, Telemetry


class TestTelemetry:
    def test_valid_creation(self):
        t = Telemetry(
            asset_id="solar-1",
            timestamp=datetime(2026, 8, 13, 12, 0, tzinfo=UTC),
            power_kw=4.2,
        )
        assert t.power_kw == 4.2
        assert t.available is True
        assert t.operating_state is OperatingState.ONLINE

    def test_required_fields(self):
        with pytest.raises(ValidationError):
            Telemetry(timestamp=datetime.now(UTC), power_kw=1.0)  # missing asset_id

    def test_naive_datetime_rejected(self):
        with pytest.raises(ValidationError):
            Telemetry(asset_id="solar-1", timestamp=datetime(2026, 8, 13, 12, 0), power_kw=1.0)

    def test_soc_lower_boundary_valid(self):
        t = Telemetry(
            asset_id="battery-1",
            timestamp=datetime.now(UTC),
            power_kw=0.0,
            soc_percent=0,
        )
        assert t.soc_percent == 0

    def test_soc_upper_boundary_valid(self):
        t = Telemetry(
            asset_id="battery-1",
            timestamp=datetime.now(UTC),
            power_kw=0.0,
            soc_percent=100,
        )
        assert t.soc_percent == 100

    def test_soc_below_zero_rejected(self):
        with pytest.raises(ValidationError):
            Telemetry(
                asset_id="battery-1",
                timestamp=datetime.now(UTC),
                power_kw=0.0,
                soc_percent=-1,
            )

    def test_soc_above_hundred_rejected(self):
        with pytest.raises(ValidationError):
            Telemetry(
                asset_id="battery-1",
                timestamp=datetime.now(UTC),
                power_kw=0.0,
                soc_percent=101,
            )

    def test_soc_optional_and_defaults_to_none(self):
        t = Telemetry(
            asset_id="solar-1", timestamp=datetime.now(UTC), power_kw=3.0
        )
        assert t.soc_percent is None

    def test_negative_energy_rejected(self):
        with pytest.raises(ValidationError):
            Telemetry(
                asset_id="solar-1",
                timestamp=datetime.now(UTC),
                power_kw=1.0,
                energy_kwh=-5,
            )

    def test_invalid_operating_state_rejected(self):
        with pytest.raises(ValidationError):
            Telemetry(
                asset_id="solar-1",
                timestamp=datetime.now(UTC),
                power_kw=1.0,
                operating_state="exploding",
            )

    def test_power_sign_convention_negative_for_consumption(self):
        charging = Telemetry(
            asset_id="ev-1", timestamp=datetime.now(UTC), power_kw=-7.2
        )
        exporting = Telemetry(
            asset_id="solar-1", timestamp=datetime.now(UTC), power_kw=5.0
        )
        assert charging.power_kw < 0
        assert exporting.power_kw > 0

    def test_serialization_roundtrip(self):
        t = Telemetry(
            asset_id="battery-1",
            timestamp=datetime(2026, 8, 13, 12, 0, tzinfo=UTC),
            power_kw=-2.0,
            soc_percent=55.0,
        )
        restored = Telemetry.model_validate(t.model_dump(mode="json"))
        assert restored == t
