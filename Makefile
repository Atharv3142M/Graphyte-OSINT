PYTHON ?= python
PIP ?= pip
NPM ?= npm

.PHONY: install install-backend install-frontend dev lint test backend-check frontend-lint frontend-build docker-up docker-down

install: install-backend install-frontend

install-backend:
	$(PIP) install -r backend/requirements.txt

install-frontend:
	cd frontend && $(NPM) install

dev:
	$(PYTHON) main.py

lint: backend-check frontend-lint

test: backend-check frontend-build

backend-check:
	$(PYTHON) -m compileall backend

frontend-lint:
	cd frontend && $(NPM) run lint

frontend-build:
	cd frontend && $(NPM) run build

docker-up:
	docker compose up -d

docker-down:
	docker compose down
