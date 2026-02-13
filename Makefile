.PHONY: install lint test build check

install:
	python -m pip install -e . pytest ruff build

lint:
	python -m ruff check .

test:
	python -m pytest -q

build:
	python -m build

check: lint test build
