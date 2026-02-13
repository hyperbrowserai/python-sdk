.PHONY: install lint format-check format test build check

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

build:
	python -m build

check: lint format-check test build
