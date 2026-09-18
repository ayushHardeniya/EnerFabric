"""Deterministic DER simulator: solar, battery, EV charger, flexible load,
critical load, and grid.

Behaves like external device infrastructure (publishing over MQTT,
eventually) rather than mutating internal application state directly,
so that simulated DERs can later be replaced by real device adapters
without changing the coordination engine or API. ``DERSimulator`` is
the entry point: build one from a tuple of ``*Config`` objects (or use
``default_fleet()``), call ``initial_state()`` then repeated ``step()``
to advance simulated time, and read off ``telemetry()``/``assets()`` —
the latter is directly usable as ``CoordinationContext.assets``.
"""

from app.simulator.devices import (
    BatteryConfig,
    CriticalLoadConfig,
    DeviceConfig,
    EVChargerConfig,
    FlexibleLoadConfig,
    GridConfig,
    SolarConfig,
)
from app.simulator.simulator import DERSimulator, default_fleet
from app.simulator.state import DeviceState, SimulationState

__all__ = [
    "BatteryConfig",
    "CriticalLoadConfig",
    "DERSimulator",
    "DeviceConfig",
    "DeviceState",
    "EVChargerConfig",
    "FlexibleLoadConfig",
    "GridConfig",
    "SimulationState",
    "SolarConfig",
    "default_fleet",
]
