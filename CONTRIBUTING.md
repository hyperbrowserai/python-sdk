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
  - `tests/test_agent_examples_coverage.py` (agent task example coverage enforcement),
  - `tests/test_agent_helper_boundary.py` (agent manager boundary enforcement for shared request/response helpers),
  - `tests/test_agent_operation_metadata_usage.py` (shared agent operation-metadata usage enforcement),
  - `tests/test_agent_payload_helper_usage.py` (shared agent start-payload helper usage enforcement),
  - `tests/test_agent_start_helper_usage.py` (shared agent start-request helper usage enforcement),
  - `tests/test_agent_stop_helper_usage.py` (shared agent stop-request helper usage enforcement),
  - `tests/test_agent_task_read_helper_usage.py` (shared agent task read-helper usage enforcement),
  - `tests/test_agent_terminal_status_helper_usage.py` (shared agent terminal-status helper usage enforcement),
  - `tests/test_architecture_marker_usage.py` (architecture marker coverage across guard modules),
  - `tests/test_binary_file_open_helper_usage.py` (shared binary file open helper usage enforcement),
  - `tests/test_browser_use_payload_helper_usage.py` (browser-use payload helper usage enforcement),
  - `tests/test_ci_workflow_quality_gates.py` (CI guard-stage + make-target enforcement),
  - `tests/test_computer_action_endpoint_helper_usage.py` (computer-action endpoint-normalization helper usage enforcement),
  - `tests/test_computer_action_payload_helper_usage.py` (computer-action payload helper usage enforcement),
  - `tests/test_contributing_architecture_guard_listing.py` (`CONTRIBUTING.md` architecture-guard inventory completeness enforcement),
  - `tests/test_core_type_helper_usage.py` (core transport/config/header/file/polling/session/error/parsing manager+tool module enforcement of shared plain-type helper usage),
  - `tests/test_default_serialization_helper_usage.py` (default optional-query serialization helper usage enforcement),
  - `tests/test_default_terminal_status_helper_usage.py` (default terminal-status helper usage enforcement for non-agent managers),
  - `tests/test_display_helper_usage.py` (display/key-format helper usage),
  - `tests/test_docs_python3_commands.py` (`README`/`CONTRIBUTING`/examples python3 command consistency enforcement),
  - `tests/test_example_run_instructions.py` (example run-instruction consistency enforcement),
  - `tests/test_example_sync_async_parity.py` (sync/async example parity enforcement),
  - `tests/test_examples_naming_convention.py` (example sync/async prefix naming enforcement),
  - `tests/test_examples_syntax.py` (example script syntax guardrail),
  - `tests/test_extension_create_helper_usage.py` (extension create-input normalization helper usage enforcement),
  - `tests/test_extract_payload_helper_usage.py` (extract start-payload helper usage enforcement),
  - `tests/test_guardrail_ast_utils.py` (shared AST guard utility contract),
  - `tests/test_job_fetch_helper_boundary.py` (centralization boundary enforcement for retry/paginated-fetch helper primitives),
  - `tests/test_job_fetch_helper_usage.py` (shared retry/paginated-fetch defaults helper usage enforcement),
  - `tests/test_job_pagination_helper_usage.py` (shared scrape/crawl pagination helper usage enforcement),
  - `tests/test_job_poll_helper_boundary.py` (centralization boundary enforcement for terminal-status polling helper primitives),
  - `tests/test_job_poll_helper_usage.py` (shared terminal-status polling helper usage enforcement),
  - `tests/test_job_query_params_helper_usage.py` (shared scrape/crawl query-param helper usage enforcement),
  - `tests/test_job_start_payload_helper_usage.py` (shared scrape/crawl start-payload helper usage enforcement),
  - `tests/test_job_wait_helper_boundary.py` (centralization boundary enforcement for wait-for-job helper primitives),
  - `tests/test_job_wait_helper_usage.py` (shared wait-for-job defaults helper usage enforcement),
  - `tests/test_makefile_quality_targets.py` (Makefile quality-gate target enforcement),
  - `tests/test_manager_model_dump_usage.py` (manager serialization centralization),
  - `tests/test_mapping_keys_access_usage.py` (centralized key-iteration boundaries),
  - `tests/test_mapping_reader_usage.py` (shared mapping-read parser usage),
  - `tests/test_optional_serialization_helper_usage.py` (optional model serialization helper usage enforcement),
  - `tests/test_page_params_helper_usage.py` (paginated manager page-params helper usage enforcement),
  - `tests/test_plain_list_helper_usage.py` (shared plain-list normalization helper usage enforcement),
  - `tests/test_plain_type_guard_usage.py` (`str`/`int` guardrail enforcement via plain-type checks),
  - `tests/test_plain_type_identity_usage.py` (direct `type(... ) is str|int` guardrail enforcement via shared helpers),
  - `tests/test_polling_defaults_usage.py` (shared polling-default constant usage enforcement across polling helper modules),
  - `tests/test_polling_loop_usage.py` (`while True` polling-loop centralization in `hyperbrowser/client/polling.py`),
  - `tests/test_pyproject_architecture_marker.py` (pytest marker registration enforcement),
  - `tests/test_readme_examples_listing.py` (README example-listing consistency enforcement),
  - `tests/test_schema_injection_helper_usage.py` (shared schema injection helper usage enforcement in payload builders),
  - `tests/test_session_profile_update_helper_usage.py` (session profile-update parameter helper usage enforcement),
  - `tests/test_session_upload_helper_usage.py` (session upload-input normalization helper usage enforcement),
  - `tests/test_start_and_wait_default_constants_usage.py` (shared start-and-wait default-constant usage enforcement),
  - `tests/test_start_job_context_helper_usage.py` (shared started-job context helper usage enforcement),
  - `tests/test_started_job_helper_boundary.py` (centralization boundary enforcement for started-job helper primitives),
  - `tests/test_tool_mapping_reader_usage.py` (tools mapping-helper usage),
  - `tests/test_type_utils_usage.py` (type `__mro__` boundary centralization in `hyperbrowser/type_utils.py`),
  - `tests/test_web_operation_metadata_usage.py` (web manager operation-metadata usage enforcement),
  - `tests/test_web_pagination_internal_reuse.py` (web pagination helper internal reuse of shared job pagination helpers),
  - `tests/test_web_payload_helper_usage.py` (web manager payload-helper usage enforcement),
  - `tests/test_web_route_constants_usage.py` (web manager route-constant usage enforcement).

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
