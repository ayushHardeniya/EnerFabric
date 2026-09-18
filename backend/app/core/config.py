"""Application settings, loaded from environment variables / .env.

Kept intentionally small for Milestone 0. Fields are added as each
milestone introduces a genuine need (database URL in Milestone 4,
MQTT broker settings in Milestone 5, etc.) rather than pre-declared
speculatively.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "EnerFabric"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"
    # Host port 5433, not the default 5432 — see docker-compose.yml's
    # postgres service comment / CLAUDE.md Milestone 4 for why.
    database_url: str = "postgresql+psycopg://enerfabric:enerfabric@localhost:5433/enerfabric"

    # MQTT broker (Mosquitto, see docker-compose.yml). ``mqtt_enabled``
    # lets the backend start (and its tests run) even when no broker is
    # reachable — a connection failure at startup is logged and the app
    # keeps serving the REST API without live telemetry ingestion, rather
    # than crashing.
    mqtt_broker_host: str = "localhost"
    mqtt_broker_port: int = 1883
    mqtt_enabled: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
