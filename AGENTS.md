# Repository Guidelines

## Project Structure & Module Organization
- `hyperbrowser/` is the Python package. Key areas: `client/` (sync + async clients and managers), `models/` (Pydantic request/response types), `transport/` (HTTP transport), `tools/` (tool schemas for integrations), plus `config.py` and `exceptions.py`.
- `tests/` is reserved for test modules (currently minimal; add new tests here).
- `README.md` contains usage examples and API key setup.
- `pyproject.toml` defines packaging metadata and dev tooling.

## Build, Test, and Development Commands
- `poetry install` — set up the virtualenv with runtime and dev dependencies.
- `poetry build` — build source and wheel distributions.
- `poetry run ruff check .` — run lint checks (ruff is the only configured dev tool).
- `poetry run ruff format .` — format code with ruff.
- Example run: create a small script using the README snippets and run with `python path/to/script.py` after setting `HYPERBROWSER_API_KEY`.

## Coding Style & Naming Conventions
- Python 3.8+ with 4‑space indentation.
- Naming: `snake_case` for modules/functions, `CamelCase` for classes, `UPPER_SNAKE_CASE` for constants.
- Prefer type hints and Pydantic models for request/response schemas.
- Use `ruff` for linting; keep code clean and import order consistent with ruff defaults.

## Testing Guidelines
- Tests live in `tests/` and should follow `test_*.py` naming.
- No test framework is wired in yet; if you add tests, include `pytest` in dev dependencies and document the command (e.g., `poetry run pytest`).

## Commit & Pull Request Guidelines
- Recent commit messages are short, imperative, and often include a PR reference like `(#45)`.
- Keep commits focused; include a clear summary and note user‑visible changes.
- PRs should describe the change, rationale, and any API impact; link issues when applicable and include small code examples for new features.

## Configuration & Secrets
- Set `HYPERBROWSER_API_KEY` via environment variables or pass `api_key=` in client constructors.
- Never commit API keys or session data; use `.env` or local shell exports for development.
