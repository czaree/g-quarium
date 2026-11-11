IMAGE ?= g-quarium
SHA := $(shell git rev-parse --short HEAD 2>/dev/null || echo dev)

.PHONY: setup test lint build dev samples clean

setup:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements-dev.txt

test:
	pytest -q

lint:
	ruff check .

build:
	docker build --build-arg GIT_SHA=$(SHA) -t $(IMAGE):dev .

dev:
	docker compose -f docker-compose.dev.yml up --build

samples:
	bash scripts/make_samples.sh

clean:
	docker compose -f docker-compose.dev.yml down -v
