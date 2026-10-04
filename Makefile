# AI Virtual Office - common tasks.
.DEFAULT_GOAL := help
.PHONY: help install dev api web test lint migrate revision seed reindex reset docker docker-down clean

BACKEND := backend
PY      := $(BACKEND)/.venv/bin/python
PIP     := $(BACKEND)/.venv/bin/pip
UVICORN := $(BACKEND)/.venv/bin/uvicorn
ALEMBIC := cd $(BACKEND) && .venv/bin/alembic

help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | \
	 awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install: ## Create the venv and install backend + frontend dependencies
	python3 -m venv $(BACKEND)/.venv
	$(PIP) install --upgrade pip
	$(PIP) install -r $(BACKEND)/requirements-dev.txt
	cd frontend && npm install
	@echo "Done. Copy backend/.env.example to backend/.env, then run: make dev"

dev: ## Run the API and the web app together
	@echo "API  -> http://localhost:8000/docs"
	@echo "Web  -> http://localhost:5173"
	@trap 'kill 0' EXIT; \
	 (cd $(BACKEND) && .venv/bin/uvicorn app.main:app --reload --port 8000) & \
	 (cd frontend && npm run dev) & \
	 wait

api: ## Run only the API
	cd $(BACKEND) && .venv/bin/uvicorn app.main:app --reload --port 8000

web: ## Run only the web app
	cd frontend && npm run dev

test: ## Run the backend test suite
	cd $(BACKEND) && .venv/bin/pytest

lint: ## Lint the backend and typecheck the frontend
	cd $(BACKEND) && .venv/bin/ruff check app tests
	cd frontend && npm run typecheck

migrate: ## Apply database migrations
	$(ALEMBIC) upgrade head

revision: ## Autogenerate a migration:  make revision m="add widgets"
	$(ALEMBIC) revision --autogenerate -m "$(m)"

reindex: ## Rebuild document search indexes (required after a tokenizer change)
	cd $(BACKEND) && .venv/bin/python -m app.cli reindex

seed: ## Seed the demo workspace into the current database
	cd $(BACKEND) && .venv/bin/python -m app.cli seed

reset: ## Drop every table and re-seed (destructive)
	cd $(BACKEND) && .venv/bin/python -m app.cli reset

docker: ## Build and start the full stack on http://localhost:8080
	docker compose up --build

docker-down: ## Stop the stack
	docker compose down

clean: ## Remove build artefacts and caches
	rm -rf frontend/dist frontend/node_modules/.vite
	find $(BACKEND) -name __pycache__ -type d -prune -exec rm -rf {} +
	rm -rf $(BACKEND)/.pytest_cache $(BACKEND)/.ruff_cache
