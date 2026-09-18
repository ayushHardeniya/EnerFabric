"""Mutable simulation state: what changes tick to tick, kept separate
from the static ``*Config`` describing each device (see ``devices.py``).
"""

from dataclasses import dataclass, field
from datetime import datetime

from app.domain import OperatingState


@dataclass(frozen=True)
class DeviceState:
    """One device's observed state at a single simulated instant.

    Mirrors the subset of ``Telemetry`` the simulator itself owns —
    ``power_kw`` follows the same sign convention (positive = net
    source, negative = net sink); ``soc_percent`` is ``None`` for
    devices with no state of charge (solar, flexible load, critical
    load, grid).
    """

    power_kw: float = 0.0
    soc_percent: float | None = None
    available: bool = True
    operating_state: OperatingState = OperatingState.ONLINE


@dataclass(frozen=True)
class SimulationState:
    """A full fleet snapshot at one simulated instant: every device's
    ``DeviceState`` keyed by asset id, plus the timestamp and step index
    that produced it. Immutable by convention — ``DERSimulator`` always
    builds a new one rather than mutating an existing one in place.
    """

    timestamp: datetime
    step: int
    devices: dict[str, DeviceState] = field(default_factory=dict)
