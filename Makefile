.PHONY: check backend-check backend-test backend-lint frontend-check

BACKEND_VENV := backend/.venv/bin

check: backend-check frontend-check

backend-check: backend-lint backend-test

backend-lint:
	$(BACKEND_VENV)/ruff check backend

backend-test:
	$(BACKEND_VENV)/pytest backend/tests

frontend-check:
	cd frontend && npm run lint