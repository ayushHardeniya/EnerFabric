"""DERSimulator: orchestrates per-device simulation steps into one
deterministic fleet simulation, and adapts the result into
domain-compatible ``Asset``/``Telemetry`` objects.

Behaves like external device infrastructure: callers advance the
simulation and read off telemetry; nothing here reaches into or
mutates coordination-engine state directly (see app/coordination). The
``telemetry()``/``assets()`` methods are also the extension point a
future MQTT publisher or API route adapts around, without needing any
changes to this module.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from app.domain import Asset, Telemetry
from app.simulator.devices import (
    BatteryConfig,
    CriticalLoadConfig,
    DeviceConfig,
    EVChargerConfig,
    FlexibleLoadConfig,
    GridConfig,
    SolarConfig,
)
from app.simulator.profiles import (
    step_battery,
    step_critical_load,
    step_ev_charger,
    step_flexible_load,
    step_grid,
    step_solar,
)
from app.simulator.state import DeviceState, SimulationState


@dataclass(frozen=True)
class DERSimulator:
    """A fixed fleet of device configs plus the tick duration used to
    integrate SOC changes. Stateless itself — all mutable simulation
    state lives in the ``SimulationState`` values it produces and
    consumes — so one simulator instance can safely drive many
    independent simulation runs (e.g. one per test) without cross-talk.
    """

    configs: tuple[DeviceConfig, ...]
    tick_minutes: float = 15.0

    def __post_init__(self) -> None:
        if self.tick_minutes <= 0:
            raise ValueError("tick_minutes must be positive")
        ids = [config.asset_id for config in self.configs]
        if len(ids) != len(set(ids)):
            raise ValueError("device configs must have unique asset_id values")
        if sum(1 for config in self.configs if isinstance(config, GridConfig)) > 1:
            raise ValueError("at most one GridConfig is supported per simulator")

    @property
    def tick_hours(self) -> float:
        return self.tick_minutes / 60.0

    def initial_state(self, start_time: datetime) -> SimulationState:
        """Seed stateful devices (battery/EV) at their configured initial
        SOC, then compute every device's state at ``start_time`` with a
        zero-length tick — nothing charges/discharges yet, but solar,
        flexible load, critical load, and grid still reflect that
        moment's schedule.
        """
        seed = {
            config.asset_id: DeviceState(soc_percent=config.initial_soc_percent)
            for config in self.configs
            if isinstance(config, BatteryConfig | EVChargerConfig)
        }
        genesis = SimulationState(timestamp=start_time, step=0, devices=seed)
        return self._compute(genesis, timestamp=start_time, step=0, tick_hours=0.0)

    def step(self, state: SimulationState) -> SimulationState:
        """Advance the simulation by one tick. Pure function of
        ``state``: the same input always produces the same output.
        """
        new_timestamp = state.timestamp + timedelta(minutes=self.tick_minutes)
        return self._compute(
            state, timestamp=new_timestamp, step=state.step + 1, tick_hours=self.tick_hours
        )

    def _compute(
        self, state: SimulationState, *, timestamp: datetime, step: int, tick_hours: float
    ) -> SimulationState:
        devices: dict[str, DeviceState] = {}
        site_net_power_kw = 0.0

        for config in self.configs:
            if isinstance(config, GridConfig):
                continue
            previous = state.devices.get(config.asset_id, DeviceState())
            new_device_state = self._step_device(config, previous, timestamp, tick_hours)
            devices[config.asset_id] = new_device_state
            site_net_power_kw += new_device_state.power_kw

        for config in self.configs:
            if isinstance(config, GridConfig):
                devices[config.asset_id] = step_grid(config, site_net_power_kw)

        return SimulationState(timestamp=timestamp, step=step, devices=devices)

    @staticmethod
    def _step_device(
        config: DeviceConfig, previous: DeviceState, timestamp: datetime, tick_hours: float
    ) -> DeviceState:
        if isinstance(config, SolarConfig):
            return step_solar(config, timestamp)
        if isinstance(config, BatteryConfig):
            return step_battery(config, previous, timestamp, tick_hours)
        if isinstance(config, EVChargerConfig):
            return step_ev_charger(config, previous, timestamp, tick_hours)
        if isinstance(config, FlexibleLoadConfig):
            return step_flexible_load(config, timestamp)
        if isinstance(config, CriticalLoadConfig):
            return step_critical_load(config, timestamp)
        raise TypeError(f"unsupported device config type: {type(config).__name__}")

    def telemetry(self, state: SimulationState) -> list[Telemetry]:
        """Domain-compatible telemetry for every device, in config
        order. This is the interface a future MQTT publisher (or any
        other adapter, or a test) consumes — the simulator never reaches
        into coordination-engine or persistence state itself.
        """
        result: list[Telemetry] = []
        for config in self.configs:
            device = state.devices[config.asset_id]
            result.append(
                Telemetry(
                    asset_id=config.asset_id,
                    timestamp=state.timestamp,
                    power_kw=device.power_kw,
                    soc_percent=device.soc_percent,
                    available=device.available,
                    operating_state=device.operating_state,
                )
            )
        return result

    def assets(self, state: SimulationState) -> list[Asset]:
        """Domain ``Asset`` objects (config + capabilities) with
        ``latest_telemetry`` populated from ``state`` — directly usable
        as ``CoordinationContext.assets``.
        """
        telemetry_by_asset = {t.asset_id: t for t in self.telemetry(state)}
        return [
            Asset(
                id=config.asset_id,
                name=config.name,
                type=config.asset_type,
                capabilities=config.capabilities(),
                latest_telemetry=telemetry_by_asset[config.asset_id],
            )
            for config in self.configs
        ]


def default_fleet(tick_minutes: float = 15.0) -> DERSimulator:
    """A ready-to-use simulator with one of each supported DER type —
    convenient for tests, demos, and later API/MQTT wiring that just
    needs believable data without hand-assembling a fleet.
    """
    return DERSimulator(
        configs=(
            SolarConfig(asset_id="solar-1"),
            BatteryConfig(asset_id="battery-1"),
            EVChargerConfig(asset_id="ev-1"),
            FlexibleLoadConfig(asset_id="flex-1"),
            CriticalLoadConfig(asset_id="crit-1"),
            GridConfig(asset_id="grid-1"),
        ),
        tick_minutes=tick_minutes,
    )
