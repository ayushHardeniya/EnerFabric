"""Standalone process that behaves like external DER device
infrastructure: advances the deterministic ``DERSimulator`` and publishes
each tick's telemetry over MQTT (see ``publisher.py``). Kept as its own
entry point, separate from the backend, so it genuinely publishes over the
network the way a real device gateway would — it never touches backend or
database state directly.

Run with ``python -m app.mqtt.run_simulator`` (see ``seed_assets.py`` for
registering matching assets first, and README.md for the full local
Mosquitto + backend + simulator setup).
"""

import argparse
import logging
import time
from datetime import UTC, datetime

from app.core.config import get_settings
from app.mqtt.publisher import TelemetryPublisher
from app.simulator.simulator import default_fleet

logger = logging.getLogger(__name__)


def run(tick_seconds: float, tick_minutes: float) -> None:
    settings = get_settings()
    simulator = default_fleet(tick_minutes=tick_minutes)
    state = simulator.initial_state(datetime.now(UTC))

    with TelemetryPublisher(
        settings.mqtt_broker_host, settings.mqtt_broker_port, client_id="enerfabric-simulator"
    ) as publisher:
        logger.info(
            "publishing simulated telemetry for %d devices to %s:%s every %ss",
            len(simulator.configs),
            settings.mqtt_broker_host,
            settings.mqtt_broker_port,
            tick_seconds,
        )
        while True:
            for telemetry in simulator.telemetry(state):
                publisher.publish(telemetry)
            time.sleep(tick_seconds)
            state = simulator.step(state)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Publish simulated DER telemetry over MQTT.")
    parser.add_argument(
        "--tick-seconds", type=float, default=5.0, help="real seconds between publishes"
    )
    parser.add_argument(
        "--tick-minutes", type=float, default=15.0, help="simulated minutes advanced per tick"
    )
    args = parser.parse_args()
    run(tick_seconds=args.tick_seconds, tick_minutes=args.tick_minutes)


if __name__ == "__main__":
    main()
