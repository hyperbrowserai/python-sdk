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
	$(PYTHON) -m pytest -q \
		tests/test_manager_model_dump_usage.py \
		tests/test_mapping_reader_usage.py \
		tests/test_mapping_keys_access_usage.py \
		tests/test_tool_mapping_reader_usage.py \
		tests/test_display_helper_usage.py

compile:
	$(PYTHON) -m compileall -q hyperbrowser examples tests

build:
	$(PYTHON) -m build

check: lint format-check compile architecture-check test build

ci: check
