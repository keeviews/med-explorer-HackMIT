PYTHON ?= python3
VENV := backend/.venv
API_HOST := 127.0.0.1
API_PORT := 18765

.PHONY: setup setup-backend setup-frontend seed build-data ingest-stub backend frontend test

setup: setup-backend setup-frontend seed

setup-backend:
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/pip install -r backend/requirements.txt

setup-frontend:
	cd frontend && npm install

seed:
	$(VENV)/bin/python scripts/seed_db.py

build-data:
	$(PYTHON) scripts/build_seed_from_openfda.py

ingest-stub:
	$(PYTHON) scripts/ingest_stub.py --dry-run

backend:
	cd backend && .venv/bin/uvicorn app.main:app --reload --host $(API_HOST) --port $(API_PORT)

frontend:
	cd frontend && npm run dev

test:
	cd backend && .venv/bin/pytest
