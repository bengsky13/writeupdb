SHELL := /bin/zsh

setup:
	python3 -m venv .venv
	. .venv/bin/activate && pip install -U pip && pip install -e backend
	cd frontend && npm install

dev:
	-docker compose down --remove-orphans
	@ids=$$(docker ps -aq --filter name='^writeupdb-'); \
	if [ -n "$$ids" ]; then docker rm -f $$ids; fi
	docker compose up --build

test:
	python3 -m pytest backend/tests

lint:
	python3 -m ruff check backend
	python3 -m mypy backend/app
	cd frontend && npm run lint

migrate:
	cd backend && alembic upgrade head

seed:
	python3 cli/main.py import-jsonl sample-data/writeups.jsonl

import-samples:
	python3 cli/main.py import-package sample-data/packages/flask-session-forgery
	python3 cli/main.py import-package sample-data/packages/pickle-deserialization-source

create-agent-token:
	python3 cli/main.py create-agent-token --name $(NAME)

reindex:
	python3 cli/main.py reindex --all

evaluate:
	python3 cli/main.py evaluate

export:
	python3 cli/main.py export ./backup

offline-test:
	python3 cli/main.py offline-test
