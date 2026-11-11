ifeq ($(OS),Windows_NT)
    PYTHON ?= py -3.12
    VENV_PY := .venv/Scripts/python.exe
else
    PYTHON ?= python3
    VENV_PY := .venv/bin/python
endif

IMAGE ?= g-quarium
SHA := $(shell git rev-parse --short HEAD 2>/dev/null || echo dev)
# Fail fast instead of silently retrying
PIP_FLAGS ?= --retries 1 --timeout 15 --disable-pip-version-check --only-binary=:all:

.PHONY: setup test lint build dev samples clean

setup:
	$(PYTHON) -m venv .venv
	$(VENV_PY) -m pip install --upgrade pip
	$(VENV_PY) -m pip install $(PIP_FLAGS) -r requirements-dev.txt

test:
	$(VENV_PY) -m pytest -q

lint:
	$(VENV_PY) -m ruff check .

build:
	docker build --build-arg GIT_SHA=$(SHA) -t $(IMAGE):dev .

dev:
	docker compose -f docker-compose.dev.yml up --build

samples:
	bash scripts/make_samples.sh

clean:
	docker compose -f docker-compose.dev.yml down -v
