# EnerFabric

**Intent-Driven Energy Orchestration Platform for Distributed Energy Resources.**

Built by team **ZenYukti** for **SRCAS Hackathon 3.0**.

EnerFabric coordinates existing distributed energy resources — rooftop
solar, EV chargers, battery storage, flexible loads, critical loads —
across a site by combining their live telemetry with what each asset
*needs or prefers* (its **intent**), plus system policies and grid
state, to produce a feasible, explainable, multi-asset allocation plan.
It is not a monitoring dashboard: it makes and explains operational
decisions.

See **[CLAUDE.md](./CLAUDE.md)** for the full product context,
architecture, domain model, technology decisions, non-goals, and
current implementation status — it is the living source of truth for
this project throughout the hackathon.

## Repository layout

```
backend/    FastAPI application (coordination engine, simulator, API, DB, MQTT, WebSockets)
frontend/   Next.js + TypeScript + Tailwind CSS product UI
infra/      Local development infrastructure config (Mosquitto)
```

## Getting started (local development)

### Prerequisites

- Python 3.11+
- Node.js 20+
- Docker + Docker Compose (for Postgres/Mosquitto)

### 1. Start local infrastructure

```bash
docker compose up -d
```

This starts PostgreSQL (`localhost:5433`) and Mosquitto (`localhost:1883`)
for local development. PostgreSQL uses host port 5433 rather than the
default 5432 to avoid colliding with unrelated PostgreSQL instances some
WSL2/Docker Desktop setups already have bound to 127.0.0.1:5432; the
container's internal port is still the standard 5432.

### 2. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload
```

The API is served at `http://localhost:8000`; check `GET /health`.

Run tests:

```bash
pytest
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

The app is served at `http://localhost:3000`.

## Running the DER simulator over MQTT

The backend subscribes to Mosquitto on startup and persists any telemetry
it receives on `enerfabric/telemetry/{asset_id}` through the same
repository/database layer the REST API uses. The DER simulator publishes
simulated device telemetry to that broker, standing in for real device
infrastructure. With infra up (step 1) and the backend running (step 2),
in two more terminals from `backend/` (with the venv activated):

```bash
# One-time per fresh database: registers the simulator's fleet
# (solar-1, battery-1, ev-1, flex-1, crit-1, grid-1) as assets, since
# telemetry for an asset that doesn't exist yet is discarded.
python -m app.mqtt.seed_assets

# Publishes simulated telemetry for that fleet every 5 real seconds
# (each publish advances the simulation by 15 simulated minutes).
python -m app.mqtt.run_simulator
```

Or, from the repository root, the equivalent Makefile targets:

```bash
make infra-up
make run-backend      # separate terminal
make seed-assets      # once, after the backend is up
make run-simulator    # separate terminal
```

Verify telemetry is flowing end-to-end via the existing REST API:

```bash
curl http://localhost:8000/api/v1/telemetry
```

Set `MQTT_ENABLED=false` in `backend/.env` to run the backend without a
broker (e.g. no Docker available) — the REST API still works, just
without live MQTT telemetry ingestion.

## Project status

Milestone 0 (repository bootstrap) is complete and has passed a strict
pre-commit audit. See [CLAUDE.md](./CLAUDE.md) §19 for current
implementation status, completed milestones, and known issues.
