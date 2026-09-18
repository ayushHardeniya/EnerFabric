"""Pure, deterministic per-device-type simulation step functions.

Each function computes a device's next ``DeviceState`` from its static
config and (where relevant) its previous state and the current
timestamp — no randomness, no I/O, no shared mutable state, mirroring
the coordination engine's own purity discipline (see
``app/coordination/engine.py``). Time-of-day scheduling (solar profile,
battery charge/discharge windows, flexible load active hours, critical
load peak hours) uses the timestamp's UTC hour-of-day; this is a
deliberate MVP simplification, not a claim about device-local time
zones.
"""

import math
from datetime import datetime

from app.domain import OperatingState
from app.simulator.devices import (
    BatteryConfig,
    CriticalLoadConfig,
    EVChargerConfig,
    FlexibleLoadConfig,
    GridConfig,
    SolarConfig,
)
from app.simulator.state import DeviceState

_EPSILON = 1e-9


def _hour_of_day(timestamp: datetime) -> float:
    return timestamp.hour + timestamp.minute / 60 + timestamp.second / 3600


def _in_window(hour: float, window: tuple[float, float]) -> bool:
    start, end = window
    return start <= hour < end


def _charge_power_kw(
    max_power_kw: float, capacity_kwh: float, soc_percent: float, tick_hours: float
) -> float:
    """Positive-magnitude charge power for this tick, capped so the
    resulting SOC never exceeds 100%.
    """
    if tick_hours <= 0:
        return 0.0
    headroom_kwh = capacity_kwh * (100.0 - soc_percent) / 100.0
    max_energy_kwh = max_power_kw * tick_hours
    energy_kwh = max(0.0, min(headroom_kwh, max_energy_kwh))
    return energy_kwh / tick_hours


def _discharge_power_kw(
    max_power_kw: float,
    capacity_kwh: float,
    soc_percent: float,
    floor_percent: float,
    tick_hours: float,
) -> float:
    """Positive-magnitude discharge power for this tick, capped so the
    resulting SOC never drops below ``floor_percent``.
    """
    if tick_hours <= 0:
        return 0.0
    available_kwh = capacity_kwh * (soc_percent - floor_percent) / 100.0
    max_energy_kwh = max_power_kw * tick_hours
    energy_kwh = max(0.0, min(available_kwh, max_energy_kwh))
    return energy_kwh / tick_hours


def _apply_soc_delta(
    soc_percent: float, power_kw: float, tick_hours: float, capacity_kwh: float
) -> float:
    """Update SOC using the domain sign convention: positive power_kw
    discharges (reduces stored energy), negative power_kw charges
    (increases it). Clamped to [0, 100] as a final safety net.
    """
    energy_delta_kwh = -power_kw * tick_hours
    new_soc = soc_percent + (energy_delta_kwh / capacity_kwh) * 100.0
    return max(0.0, min(100.0, new_soc))


def step_solar(config: SolarConfig, timestamp: datetime) -> DeviceState:
    """Deterministic half-sine generation profile between sunrise and
    sunset, zero outside daylight hours. Stateless: output depends only
    on time of day, never on a prior tick.
    """
    hour = _hour_of_day(timestamp)
    if _in_window(hour, (config.sunrise_hour, config.sunset_hour)):
        daylight_span = config.sunset_hour - config.sunrise_hour
        fraction = math.sin(math.pi * (hour - config.sunrise_hour) / daylight_span)
        power_kw = max(0.0, config.max_power_kw * fraction)
    else:
        power_kw = 0.0
    operating_state = OperatingState.ACTIVE if power_kw > _EPSILON else OperatingState.IDLE
    return DeviceState(power_kw=round(power_kw, 4), operating_state=operating_state)


def step_battery(
    config: BatteryConfig, previous: DeviceState, timestamp: datetime, tick_hours: float
) -> DeviceState:
    """Charges during ``charge_window`` up to 100% SOC, discharges during
    ``discharge_window`` down to ``reserve_percent``, holds otherwise.
    """
    soc = previous.soc_percent if previous.soc_percent is not None else config.initial_soc_percent
    hour = _hour_of_day(timestamp)

    if _in_window(hour, config.charge_window) and soc < 100.0:
        power_kw = -_charge_power_kw(config.max_charge_kw, config.capacity_kwh, soc, tick_hours)
    elif _in_window(hour, config.discharge_window) and soc > config.reserve_percent:
        power_kw = _discharge_power_kw(
            config.max_discharge_kw, config.capacity_kwh, soc, config.reserve_percent, tick_hours
        )
    else:
        power_kw = 0.0

    operating_state = OperatingState.ACTIVE if abs(power_kw) > _EPSILON else OperatingState.IDLE
    new_soc = _apply_soc_delta(soc, power_kw, tick_hours, config.capacity_kwh)
    return DeviceState(
        power_kw=round(power_kw, 4), soc_percent=round(new_soc, 4), operating_state=operating_state
    )


def step_ev_charger(
    config: EVChargerConfig, previous: DeviceState, timestamp: datetime, tick_hours: float
) -> DeviceState:
    """Charges toward 100% SOC whenever it isn't already there; holds
    once full.
    """
    soc = previous.soc_percent if previous.soc_percent is not None else config.initial_soc_percent

    if soc < 100.0:
        power_kw = -_charge_power_kw(config.max_power_kw, config.capacity_kwh, soc, tick_hours)
    else:
        power_kw = 0.0

    operating_state = OperatingState.ACTIVE if abs(power_kw) > _EPSILON else OperatingState.IDLE
    new_soc = _apply_soc_delta(soc, power_kw, tick_hours, config.capacity_kwh)
    return DeviceState(
        power_kw=round(power_kw, 4), soc_percent=round(new_soc, 4), operating_state=operating_state
    )


def step_flexible_load(config: FlexibleLoadConfig, timestamp: datetime) -> DeviceState:
    """Draws its full controllable demand during ``active_window``,
    nothing outside it. Stateless.
    """
    hour = _hour_of_day(timestamp)
    active = _in_window(hour, config.active_window)
    power_kw = -config.max_power_kw if active else 0.0
    operating_state = OperatingState.ACTIVE if active else OperatingState.IDLE
    return DeviceState(power_kw=power_kw, operating_state=operating_state)


def step_critical_load(config: CriticalLoadConfig, timestamp: datetime) -> DeviceState:
    """Mandatory demand: never zero, higher during ``peak_window``.
    Stateless.
    """
    hour = _hour_of_day(timestamp)
    peak = _in_window(hour, config.peak_window)
    power_kw = -(config.peak_power_kw if peak else config.base_power_kw)
    return DeviceState(power_kw=power_kw, operating_state=OperatingState.ACTIVE)


def step_grid(config: GridConfig, site_net_power_kw: float) -> DeviceState:
    """The grid offsets whatever the rest of the site could not balance
    itself. ``site_net_power_kw`` is the sum of every other device's
    power_kw this tick (positive = site-wide surplus, negative =
    deficit); the grid's own power_kw mirrors that, clipped to its
    configured import/export limits. An unavailable grid contributes
    nothing regardless of site imbalance — the resulting shortfall is
    for the coordination engine to report as infeasible, not something
    the simulator silently resolves.
    """
    if not config.available:
        return DeviceState(power_kw=0.0, available=False, operating_state=OperatingState.OFFLINE)

    required_kw = -site_net_power_kw
    if required_kw > 0 and config.import_limit_kw is not None:
        power_kw = min(required_kw, config.import_limit_kw)
    elif required_kw < 0 and config.export_limit_kw is not None:
        power_kw = max(required_kw, -config.export_limit_kw)
    else:
        power_kw = required_kw

    operating_state = OperatingState.ACTIVE if abs(power_kw) > _EPSILON else OperatingState.IDLE
    return DeviceState(power_kw=round(power_kw, 4), operating_state=operating_state)
