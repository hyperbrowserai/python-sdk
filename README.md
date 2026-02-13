# Hyperbrowser Python SDK

Python SDK for the Hyperbrowser API.

- Full docs: https://hyperbrowser.ai/docs
- Package: https://pypi.org/project/hyperbrowser/

## Requirements

- Python `>=3.9`

## Installation

```bash
pip install hyperbrowser
```

## Configuration

You can pass credentials directly, or use environment variables.

```bash
export HYPERBROWSER_API_KEY="your_api_key"
export HYPERBROWSER_BASE_URL="https://api.hyperbrowser.ai" # optional
export HYPERBROWSER_HEADERS='{"X-Correlation-Id":"req-123"}' # optional JSON object
```

`api_key` must be a non-empty string and must not contain control characters.

`base_url` must start with `https://` (or `http://` for local testing), include a host,
and not contain query parameters, URL fragments, backslashes, control characters,
or whitespace/newline characters.
`base_url` must not include embedded user credentials.
If a port is provided in `base_url`, it must be a valid numeric port.
Unsafe encoded host/path forms (for example encoded traversal segments or encoded host/path delimiters) are also rejected.
Excessively nested URL encoding in base URLs and internal API paths is rejected.
The SDK normalizes trailing slashes automatically.
If `base_url` already ends with `/api`, the SDK avoids adding a duplicate `/api` prefix.
If `HYPERBROWSER_BASE_URL` is set, it must be non-empty.
When `config` is not provided, client constructors also read `HYPERBROWSER_HEADERS`
automatically (same as API key and base URL).
Internal request paths are validated as relative API paths and reject fragments,
unsafe traversal segments, encoded query/fragment delimiters, backslashes, and
whitespace/control characters. Unencoded whitespace/control characters in query
strings are also rejected.

You can also pass custom headers (for tracing/correlation) either via
`ClientConfig` or directly to the client constructor.
Header keys/values must be strings; header names are trimmed, must use valid HTTP
token characters, must be 256 characters or fewer, and control characters are rejected.
Duplicate header names are rejected after normalization (case-insensitive), e.g.
`"X-Trace"` with `"  X-Trace  "` or `"x-trace"`.

```python
from hyperbrowser import ClientConfig, Hyperbrowser

config = ClientConfig(
    api_key="your_api_key",
    headers={"X-Correlation-Id": "req-123"},
)

with Hyperbrowser(config=config) as client:
    ...
```

```python
from hyperbrowser import Hyperbrowser

with Hyperbrowser(
    api_key="your_api_key",
    headers={"X-Correlation-Id": "req-123"},
) as client:
    ...
```

> If you pass `config=...`, do not also pass `api_key`, `base_url`, or `headers`.
> `timeout` may be provided to client constructors and must be finite and non-negative (`None` disables request timeouts).

## Clients

The SDK provides both sync and async clients with mirrored APIs:

- `Hyperbrowser` (sync)
- `AsyncHyperbrowser` (async)

### Sync quickstart

```python
from hyperbrowser import Hyperbrowser

with Hyperbrowser(api_key="your_api_key") as client:
    session = client.sessions.create()
    print(session.id, session.ws_endpoint)
    client.sessions.stop(session.id)
```

### Async quickstart

```python
import asyncio
from hyperbrowser import AsyncHyperbrowser

async def main() -> None:
    async with AsyncHyperbrowser(api_key="your_api_key") as client:
        session = await client.sessions.create()
        print(session.id, session.ws_endpoint)
        await client.sessions.stop(session.id)

asyncio.run(main())
```

## Main manager surface

Both clients expose:

- `client.sessions`
- `client.scrape` (+ `client.scrape.batch`)
- `client.crawl`
- `client.extract`
- `client.web` (+ `client.web.batch_fetch`, `client.web.crawl`)
- `client.agents` (`browser_use`, `cua`, `claude_computer_use`, `gemini_computer_use`, `hyper_agent`)
- `client.profiles`
- `client.extensions`
- `client.team`
- `client.computer_action`

For file uploads (session uploads, extension uploads), provided paths must reference existing files (not directories), must not contain control characters, and must not include leading/trailing whitespace. File-like upload objects must expose a callable `read()` and remain open.

## Job polling (`start_and_wait`)

Long-running APIs expose `start_and_wait(...)`.

These methods now support explicit polling controls:

- `poll_interval_seconds` (default `2.0`)
- `max_wait_seconds` (default `600.0`)
- `max_status_failures` (default `5`)

Timing values must be finite, non-negative numbers.
Polling callback contracts are also validated:

- Sync polling helpers require non-awaitable callback return values.
- Async polling helpers require awaitable status/page/retry callbacks.
- Polling retries skip non-retryable API client errors (HTTP `4xx`, except retryable `408` request-timeout and `429` rate-limit responses).
- Retry classification accepts integer, ASCII numeric-string, and ASCII numeric byte-string HTTP status metadata when evaluating retryability (including wait-helper status/fetch paths); malformed/oversized/non-ASCII values safely fall back to retryable unknown behavior.
- SDK timeout/polling exceptions (`HyperbrowserTimeoutError`, `HyperbrowserPollingError`) are treated as non-retryable and are surfaced immediately.
- Cancellation exceptions are treated as non-retryable and are surfaced immediately.
- Broken executor errors are treated as non-retryable and are surfaced immediately.
- Invalid-state errors are treated as non-retryable and are surfaced immediately.
- Callback contract violations and callback execution failures fail fast with explicit callback-specific errors.
- Reused coroutine callback errors (e.g. `cannot reuse already awaited coroutine`) are treated as non-retryable and surfaced immediately.
- Async generator reuse runtime errors (e.g. `asynchronous generator is already running`) are treated as non-retryable and surfaced immediately.
- Generator reentrancy errors (e.g. `generator already executing`) are treated as non-retryable and surfaced immediately.
- Iterator exhaustion callback errors (`StopIteration` / `StopAsyncIteration`) are treated as non-retryable and surfaced immediately.
- Async loop contract runtime errors (e.g. `Future attached to a different loop`, `Task is bound to a different event loop`, `Non-thread-safe operation invoked on an event loop other than the current one`, `Event loop is closed`) are treated as non-retryable and surfaced immediately.
- Executor-shutdown runtime errors (e.g. `cannot schedule new futures after shutdown`) are treated as non-retryable and surfaced immediately.
- Wait helpers (`start_and_wait`, `wait_for_job_result`) only execute fetch/result callbacks after terminal status is reached; polling failures/timeouts short-circuit before fetch retries begin.

Example:

```python
from hyperbrowser import Hyperbrowser
from hyperbrowser.models import StartExtractJobParams

with Hyperbrowser(api_key="your_api_key") as client:
    result = client.extract.start_and_wait(
        StartExtractJobParams(
            urls=["https://hyperbrowser.ai"],
            prompt="Extract the main headline",
        ),
        poll_interval_seconds=1.5,
        max_wait_seconds=300,
        max_status_failures=5,
    )
    print(result.status, result.data)
```

## Error handling

SDK errors are raised as `HyperbrowserError`.
Polling timeouts and repeated polling failures are surfaced as:

- `HyperbrowserTimeoutError`
- `HyperbrowserPollingError`

`HyperbrowserPollingError` also covers stalled pagination (no page-batch progress during result collection).
Transport-level request failures include HTTP method + URL context in error messages.

```python
from hyperbrowser import Hyperbrowser
from hyperbrowser.exceptions import (
    HyperbrowserError,
    HyperbrowserTimeoutError,
)
from hyperbrowser.models import StartScrapeJobParams

try:
    with Hyperbrowser(api_key="invalid") as client:
        client.team.get_credit_info()
except HyperbrowserError as exc:
    print(exc)

try:
    with Hyperbrowser(api_key="your_api_key") as client:
        client.scrape.start_and_wait(
            StartScrapeJobParams(url="https://example.com"),
            max_wait_seconds=5,
        )
except HyperbrowserTimeoutError:
    print("Scrape job timed out")
```

## Development

```bash
pip install -e . pytest ruff build
python -m ruff check .
python -m ruff format --check .
python -m pytest -q
python -m build
```

Or use Make targets:

```bash
make install
make check
make ci
```

## Examples

Ready-to-run examples are available in `examples/`:

- `examples/sync_scrape.py`
- `examples/async_extract.py`

## License

MIT — see [LICENSE](LICENSE).
