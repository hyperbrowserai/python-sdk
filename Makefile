.PHONY: install lint format-check format compile test build check ci

install:
	python -m pip install -e . pytest ruff build

lint:
	python -m ruff check .

format-check:
	python -m ruff format --check .

format:
	python -m ruff format .

test:
	python -m pytest -q

compile:
	python -m compileall -q hyperbrowser examples tests

build:
	python -m build

check: lint format-check compile test build

ci: check
