# Getting Started

Local development setup for EnerFabric. For the live deployment, see
[deployment.md](deployment.md).

## Prerequisites

- Python 3.11+
- Node.js 20+
- Docker + Docker Compose v2

## 1. Clone and configure

```bash
git clone https://github.com/ayushHardeniya/EnerFabric.git
cd EnerFabric
```

## 2. Start local infrastructure

```bash
make infra-up
# equivalent to: docker compose up -d postgres mosquitto
```

Starts PostgreSQL on `localhost:5433` (not the default 5432 — avoids
colliding with a PostgreSQL instance some WSL2/Docker Desktop setups
already bind to `127.0.0.1:5432`; the container's internal port is
still 5432) and Mosquitto on `localhost:1883`.

`docker-compose.yml` also defines `backend`/`frontend`/`simulator`/
`nginx` services used for the full-stack deployment (see
[deployment.md](deployment.md)) — `make infra-up` deliberately starts
only `postgres`/`mosquitto` so local dev runs the backend and frontend
as regular host processes, per steps 3–4 below.

## 3. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload
# or, from the repo root: make run-backend
```

Serves the API at `http://localhost:8000`. Check `GET /health`.

Run the test suite and linter:

```bash
pytest
ruff check .
# or, from the repo root: make backend-check
```

## 4. Frontend

```bash
cd frontend
npm install
cp .env.example .env.local   # NEXT_PUBLIC_API_URL, defaults to http://localhost:8000
npm run dev
```

Serves the dashboard at `http://localhost:3000`. The WebSocket URL is
derived from `NEXT_PUBLIC_API_URL` automatically (see
`frontend/src/lib/config.ts`).

## 5. Simulator (DER telemetry over MQTT)

The backend subscribes to Mosquitto on startup and persists any
telemetry received on `enerfabric/telemetry/{asset_id}` through the
same repository/database layer the REST API uses. The DER simulator
publishes simulated device telemetry to that broker, standing in for
real device infrastructure.

With infra up and the backend running, in two more terminals from
`backend/` (venv activated):

```bash
# One-time per fresh database: registers the simulator's fleet
# (solar-1, battery-1, ev-1, flex-1, crit-1, grid-1) as assets —
# telemetry for an asset that doesn't exist yet is discarded.
python -m app.mqtt.seed_assets
# or: make seed-assets

# Publishes simulated telemetry for that fleet every 5 real seconds
# (each publish advances the simulation by 15 simulated minutes).
python -m app.mqtt.run_simulator
# or: make run-simulator
```

Set `MQTT_ENABLED=false` in `backend/.env` to run the backend without a
broker — the REST API still works, just without live telemetry
ingestion.

## 6. Verify

```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/assets
curl http://localhost:8000/api/v1/telemetry
```

Trigger a coordination run and watch it broadcast live over WebSocket:

```bash
curl -X POST http://localhost:8000/api/v1/coordination/runs \
  -H 'Content-Type: application/json' -d '{"trigger_reason":"manual"}'
```

Open `http://localhost:3000` — the Overview page should show the
backend as connected, the seeded asset fleet, and telemetry updating
live as the simulator publishes. The Coordination page shows the
decision and its per-asset explanation.

## Stopping services

```bash
# Backend / frontend / simulator: Ctrl-C in their respective terminals

make infra-down
# equivalent to: docker compose down
```

`docker compose down -v` additionally removes the `postgres_data`
volume, destroying the local database.

## Full command reference

All of the above are also available as `Makefile` targets from the
repo root — see [`Makefile`](../Makefile) for the complete list
(`infra-up`, `infra-down`, `run-backend`, `seed-assets`,
`run-simulator`, `backend-check`, `frontend-check`, `check`).
