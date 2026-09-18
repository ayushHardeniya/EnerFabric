.PHONY: check backend-check backend-test backend-lint frontend-check \
	infra-up infra-down run-backend seed-assets run-simulator

BACKEND_VENV := backend/.venv/bin

check: backend-check frontend-check

backend-check: backend-lint backend-test

backend-lint:
	$(BACKEND_VENV)/ruff check backend

backend-test:
	$(BACKEND_VENV)/pytest backend/tests

frontend-check:
	cd frontend && npm run lint

# Local Milestone 5 (MQTT) run flow: `make infra-up`, then in separate
# terminals `make run-backend` and (after `make seed-assets` once)
# `make run-simulator`. See README.md for the full walkthrough.

infra-up:
	docker compose up -d

infra-down:
	docker compose down

run-backend:
	cd backend && .venv/bin/uvicorn app.main:app --reload

seed-assets:
	cd backend && .venv/bin/python -m app.mqtt.seed_assets

run-simulator:
	cd backend && .venv/bin/python -m app.mqtt.run_simulator