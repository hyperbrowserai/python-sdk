# Contributing to Hyperbrowser Python SDK

Thanks for contributing! This guide keeps local development and CI behavior aligned.

## Prerequisites

- Python `>=3.9`
- `pip`

## Local setup

```bash
python3 -m pip install -e . pytest ruff build
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
python3 -m ruff check .
python3 -m ruff format --check .
```

Or:

```bash
make lint
make format-check
```

### Tests

```bash
python3 -m pytest -q
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
  - `tests/test_architecture_marker_usage.py` (architecture marker coverage across guard modules),
  - `tests/test_ci_workflow_quality_gates.py` (CI guard-stage + make-target enforcement),
  - `tests/test_computer_action_endpoint_helper_usage.py` (computer-action endpoint-normalization helper usage enforcement),
  - `tests/test_contributing_architecture_guard_listing.py` (`CONTRIBUTING.md` architecture-guard inventory completeness enforcement),
  - `tests/test_core_type_helper_usage.py` (core transport/config/header/file/polling/session/error/parsing manager+tool module enforcement of shared plain-type helper usage),
  - `tests/test_display_helper_usage.py` (display/key-format helper usage),
  - `tests/test_docs_python3_commands.py` (`README`/`CONTRIBUTING`/examples python3 command consistency enforcement),
  - `tests/test_example_run_instructions.py` (example run-instruction consistency enforcement),
  - `tests/test_example_sync_async_parity.py` (sync/async example parity enforcement),
  - `tests/test_examples_syntax.py` (example script syntax guardrail),
  - `tests/test_guardrail_ast_utils.py` (shared AST guard utility contract),
  - `tests/test_makefile_quality_targets.py` (Makefile quality-gate target enforcement),
  - `tests/test_manager_model_dump_usage.py` (manager serialization centralization),
  - `tests/test_mapping_keys_access_usage.py` (centralized key-iteration boundaries),
  - `tests/test_mapping_reader_usage.py` (shared mapping-read parser usage),
  - `tests/test_optional_serialization_helper_usage.py` (optional model serialization helper usage enforcement),
  - `tests/test_plain_list_helper_usage.py` (shared plain-list normalization helper usage enforcement),
  - `tests/test_plain_type_guard_usage.py` (`str`/`int` guardrail enforcement via plain-type checks),
  - `tests/test_plain_type_identity_usage.py` (direct `type(... ) is str|int` guardrail enforcement via shared helpers),
  - `tests/test_polling_loop_usage.py` (`while True` polling-loop centralization in `hyperbrowser/client/polling.py`),
  - `tests/test_pyproject_architecture_marker.py` (pytest marker registration enforcement),
  - `tests/test_readme_examples_listing.py` (README example-listing consistency enforcement),
  - `tests/test_session_upload_helper_usage.py` (session upload-input normalization helper usage enforcement),
  - `tests/test_tool_mapping_reader_usage.py` (tools mapping-helper usage),
  - `tests/test_type_utils_usage.py` (type `__mro__` boundary centralization in `hyperbrowser/type_utils.py`),
  - `tests/test_web_payload_helper_usage.py` (web manager payload-helper usage enforcement).

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
