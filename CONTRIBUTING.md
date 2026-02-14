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

### Full local CI parity

```bash
make ci
```

This runs lint, format checks, compile checks, tests, and package build.

## Testing guidance

- Add tests for any bug fix or behavior change.
- Keep sync/async behavior in parity where applicable.
- Prefer deterministic unit tests over network-dependent tests.

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
