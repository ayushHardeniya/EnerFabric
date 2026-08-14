.PHONY: check backend-check backend-test backend-lint frontend-check \
	infra-up infra-down run-backend seed-assets run-simulator \
	deploy-up deploy-down

BACKEND_VENV := backend/.venv/bin

check: backend-check frontend-check

backend-check: backend-lint backend-test

backend-lint:
	$(BACKEND_VENV)/ruff check backend

backend-test:
	$(BACKEND_VENV)/pytest backend/tests

frontend-check:
	cd frontend && npm run lint

# Local dev flow (backend/frontend run as host processes, not
# containers): `make infra-up`, then in separate terminals
# `make run-backend` and (after `make seed-assets` once)
# `make run-simulator`. See README.md for the full walkthrough.
#
# infra-up only starts postgres/mosquitto — docker-compose.yml also
# defines backend/frontend/simulator services for full-stack deployment
# (see `deploy-up` below and README.md's Deployment section), which
# infra-up deliberately does not start, to keep this local flow
# unchanged.

infra-up:
	docker compose up -d postgres mosquitto

infra-down:
	docker compose down

run-backend:
	cd backend && .venv/bin/uvicorn app.main:app --reload

seed-assets:
	cd backend && .venv/bin/python -m app.mqtt.seed_assets

run-simulator:
	cd backend && .venv/bin/python -m app.mqtt.run_simulator

# Full-stack deployment (see README.md's Deployment section):
# postgres, mosquitto, backend, frontend, and the DER simulator all as
# containers, in the same docker-compose.yml.
deploy-up:
	docker compose up -d --build

deploy-down:
	docker compose down