"""One-time convenience script: registers ``default_fleet()``'s devices as
persisted assets with ids matching the simulator's ``asset_id`` values, so
a fresh database has assets for the simulator's published telemetry to
attach to (telemetry for an unregistered asset is discarded — see
``service.persist_telemetry``).

Not part of the MQTT runtime flow itself — asset registration is its own
concern, separate from telemetry ingestion (see CLAUDE.md's architecture
diagram: "Asset Registry" is distinct from "Telemetry"). This exists only
so Milestone 5's local setup can go from a clean database to a
demonstrable end-to-end result without manually posting six assets by
hand. Writes directly through the repository layer (not the REST API)
because asset creation via ``POST /api/v1/assets`` always server-generates
a random id, whereas the simulator needs specific, known ids.

Run with ``python -m app.mqtt.seed_assets``.
"""

import logging

from app.db import repository as repo
from app.db.session import SessionLocal
from app.domain import Asset
from app.simulator.simulator import default_fleet

logger = logging.getLogger(__name__)


def seed_default_fleet_assets() -> None:
    db = SessionLocal()
    try:
        for config in default_fleet().configs:
            if repo.get_asset(db, config.asset_id) is not None:
                logger.info("asset %s already exists, skipping", config.asset_id)
                continue
            asset = Asset(
                id=config.asset_id,
                name=config.name,
                type=config.asset_type,
                capabilities=config.capabilities(),
            )
            repo.create_asset(db, asset)
            logger.info("registered asset %s (%s)", asset.id, asset.type.value)
    finally:
        db.close()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    seed_default_fleet_assets()


if __name__ == "__main__":
    main()
