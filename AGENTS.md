# Repository Guidelines

## Project Structure & Module Organization
- `hyperbrowser/` is the Python package. Key areas: `client/` (sync + async clients and managers), `types/` (TypedDict request types), `models/` (Pydantic responses and legacy-compatible request classes), `transport/` (HTTP transport), `tools/` (tool schemas for integrations), plus `config.py` and `exceptions.py`.
- `tests/` is reserved for test modules (currently minimal; add new tests here).
- `README.md` contains usage examples and API key setup.
- `pyproject.toml` defines packaging metadata and dev tooling.

## Build, Test, and Development Commands
- Use Python 3.12 for the Poetry development environment; the runtime package is tested on Python 3.8 through 3.14.
- `poetry install` — set up the virtualenv with runtime and dev dependencies.
- `poetry build` — build source and wheel distributions.
- `poetry run ruff check .` — run lint checks.
- `poetry run ruff format .` — format code with ruff.
- `poetry run pytest tests --ignore=tests/sandbox/e2e` — run the local non-E2E suite.
- Example run: create a small script using the README snippets and run with `python path/to/script.py` after setting `HYPERBROWSER_API_KEY`.

## Coding Style & Naming Conventions
- Python 3.8+ with 4‑space indentation.
- Naming: `snake_case` for modules/functions, `CamelCase` for classes, `UPPER_SNAKE_CASE` for constants.
- Prefer TypedDicts for new request schemas and Pydantic models for responses. Preserve the legacy Pydantic request path when changing an existing API.
- Use `ruff` for linting; keep code clean and import order consistent with ruff defaults.

## Testing Guidelines
- Tests live in `tests/` and should follow `test_*.py` naming.
- Add runtime compatibility coverage for both dictionaries and legacy Pydantic request objects when changing a request path.
- Keep the mypy and Pyright fixtures under `tests/typecheck/` in sync with public request annotations.

## Commit & Pull Request Guidelines
- Recent commit messages are short, imperative, and often include a PR reference like `(#45)`.
- Keep commits focused; include a clear summary and note user‑visible changes.
- PRs should describe the change, rationale, and any API impact; link issues when applicable and include small code examples for new features.

## Configuration & Secrets
- Set `HYPERBROWSER_API_KEY` via environment variables or pass `api_key=` in client constructors.
- Never commit API keys or session data; use `.env` or local shell exports for development.

## Cursor Cloud specific instructions

### Dev commands

- `poetry install` — install all dependencies
- `poetry run ruff check .` — lint (pre-existing warnings are expected in the
  current codebase)
- `poetry run ruff format .` — auto-format
- `poetry run pytest` — run tests (pytest is a dev dependency)

### Gotchas

- Use Python 3.12 for the Poetry environment. Runtime compatibility with other
  supported Python versions is exercised by CI.
- Poetry must be on `PATH`. The Cloud Agent VM installs it via
  `pip3 install poetry`; the binary lands in `~/.local/bin`.
