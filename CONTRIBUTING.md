# Contributing to Hyperbrowser Python SDK

Thanks for contributing! This guide keeps local development and CI behavior aligned.

## Prerequisites

- Python `>=3.9`
- `pip`

## Local setup

```bash
python -m pip install -e . pytest ruff build
```

Or with Make:

```bash
make install
```

## Development workflow

1. Create a focused branch.
2. Make a single logical change.
3. Run relevant tests first (targeted), then full checks before opening a PR.
4. Keep commits small and descriptive.

## Commands

### Linting and formatting

```bash
python -m ruff check .
python -m ruff format --check .
```

Or:

```bash
make lint
make format-check
```

### Tests

```bash
python -m pytest -q
```

Or:

```bash
make test
```

### Architecture guard suites

```bash
make architecture-check
```

This runs `pytest -m architecture` against guardrail suites.

### Full local CI parity

```bash
make ci
```

This runs lint, format checks, compile checks, tests, and package build.

## Testing guidance

- Add tests for any bug fix or behavior change.
- Keep sync/async behavior in parity where applicable.
- Prefer deterministic unit tests over network-dependent tests.
- Preserve architectural guardrails with focused tests. Current guard suites include:
  - `tests/test_guardrail_ast_utils.py` (shared AST guard utility contract),
  - `tests/test_manager_model_dump_usage.py` (manager serialization centralization),
  - `tests/test_mapping_reader_usage.py` (shared mapping-read parser usage),
  - `tests/test_mapping_keys_access_usage.py` (centralized key-iteration boundaries),
  - `tests/test_tool_mapping_reader_usage.py` (tools mapping-helper usage),
  - `tests/test_display_helper_usage.py` (display/key-format helper usage),
  - `tests/test_ci_workflow_quality_gates.py` (CI guard-stage + make-target enforcement),
  - `tests/test_makefile_quality_targets.py` (Makefile quality-gate target enforcement),
  - `tests/test_pyproject_architecture_marker.py` (pytest marker registration enforcement).

## Code quality conventions

- Prefer explicit error messages with `HyperbrowserError`.
- Preserve `original_error` for wrapped runtime failures.
- Avoid mutating user-provided input payloads.
- Keep sync and async manager APIs aligned.

## Pull request checklist

- [ ] Lint and format checks pass.
- [ ] Tests pass locally.
- [ ] New behavior is covered by tests.
- [ ] Public API changes are documented in `README.md` (if applicable).
