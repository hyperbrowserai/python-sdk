.PHONY: install lint format-check format compile test architecture-check build check ci

PYTHON ?= python3

install:
	$(PYTHON) -m pip install -e . pytest ruff build

lint:
	$(PYTHON) -m ruff check .

format-check:
	$(PYTHON) -m ruff format --check .

format:
	$(PYTHON) -m ruff format .

test:
	$(PYTHON) -m pytest -q

architecture-check:
	$(PYTHON) -m pytest -q -m architecture

compile:
	$(PYTHON) -m compileall -q hyperbrowser examples tests

build:
	$(PYTHON) -m build

check: lint format-check compile architecture-check test build

ci: check
