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
> `timeout` may be provided to client constructors and must be finite and non-negative (`None` disables request timeouts). Numeric timeout inputs (including `Decimal`/`Fraction`) are normalized to float values before being applied to the underlying HTTP client.

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

Timing values must be finite, non-negative numbers (including `Decimal`/`Fraction` inputs).
Polling callback contracts are also validated:

- Sync polling helpers require non-awaitable callback return values.
- Async polling helpers require awaitable status/page/retry callbacks.
- Polling retries skip non-retryable API client errors (HTTP `4xx`, except retryable `408` request-timeout and `429` rate-limit responses).
- Retry classification accepts integer, ASCII unsigned numeric-string, and ASCII unsigned numeric byte-string HTTP status metadata (including bytes-like inputs such as `bytearray`/`memoryview`) when evaluating retryability (including wait-helper status/fetch paths); malformed/oversized/signed/non-ASCII values safely fall back to retryable unknown behavior.
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
- SDK-managed job operation labels derived from job IDs are automatically normalized and bounded (whitespace normalization/trimming, control-character cleanup, and truncation) to satisfy polling operation-name validation limits; internal fetch-step labels inherit the same normalization guarantees while preserving `Fetching ...` context (with truncation if needed).
- Fetch-step operation labels are normalized idempotently; already-prefixed `Fetching ...` labels are preserved (not double-prefixed), including case-insensitive `fetching ...` variants, bare `fetching` keyword labels, and non-alphanumeric separator forms like `fetching?...` / `fetching...`.

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

## Prebuilt tool wrappers

`hyperbrowser.tools` exposes prebuilt wrappers for common tool-calling flows (`WebsiteScrapeTool`, `WebsiteScreenshotTool`, `WebsiteCrawlTool`, `WebsiteExtractTool`, `BrowserUseTool`).

Input and output normalization guarantees:

- Tool params must be a mapping with **string keys** (no blank keys, no leading/trailing whitespace keys, no control characters in keys).
- Extract tool `schema` accepts:
  - a JSON object mapping, or
  - a JSON string that decodes to a JSON object.
- Extract `schema` mapping keys must be strings.
- Tool response objects must expose a `data` field (attribute-based or mapping-based response wrappers are supported).
- Text output fields support UTF-8 bytes-like values (`bytes`, `bytearray`, `memoryview`) and decode them to strings.
- Invalid UTF-8 text payloads raise deterministic `HyperbrowserError` diagnostics.
- Extract tool output serialization enforces strict JSON (for example, non-standard values like `NaN`/`Infinity` are rejected).

## Error handling

SDK errors are raised as `HyperbrowserError`.
Polling timeouts and repeated polling failures are surfaced as:

- `HyperbrowserTimeoutError`
- `HyperbrowserPollingError`

`HyperbrowserPollingError` also covers stalled pagination (no page-batch progress during result collection).
Transport-level request failures include HTTP method + URL context in error messages.
Method-like fallback objects are stringified for diagnostics (with strict token validation), bytes-like fallback methods/URLs are decoded when valid, malformed/sentinel method inputs (for example `null`/`undefined`/`true`/`false`/`nan` or numeric-like values such as `1`/`1.5`/`1e3`) are normalized to `UNKNOWN`, and missing/malformed/sentinel URL inputs (for example `None`, booleans, invalid bytes, `null`/`undefined`/`true`/`false`/`nan`, or numeric-like values such as `123`/`1.5`/`1e6`) are normalized to `unknown URL`.

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
python3 -m pip install -e . pytest ruff build
python3 -m ruff check .
python3 -m ruff format --check .
python3 -m pytest -q
python3 -m build
```

Or use Make targets:

```bash
make install
make architecture-check
make check
make ci
```

`make architecture-check` runs fast architecture guard suites
(shared-helper adoption and quality-gate workflow checks) via `pytest -m architecture`.

Contributor workflow details are available in [CONTRIBUTING.md](CONTRIBUTING.md).

## Examples

Ready-to-run examples are available in `examples/`:

- `examples/async_batch_fetch.py`
- `examples/async_crawl.py`
- `examples/async_extension_list.py`
- `examples/async_extract.py`
- `examples/async_profile_list.py`
- `examples/async_scrape.py`
- `examples/async_session_list.py`
- `examples/async_team_credit_info.py`
- `examples/async_web_crawl.py`
- `examples/async_web_fetch.py`
- `examples/async_web_search.py`
- `examples/sync_batch_fetch.py`
- `examples/sync_crawl.py`
- `examples/sync_extension_list.py`
- `examples/sync_extract.py`
- `examples/sync_profile_list.py`
- `examples/sync_scrape.py`
- `examples/sync_session_list.py`
- `examples/sync_team_credit_info.py`
- `examples/sync_web_crawl.py`
- `examples/sync_web_fetch.py`
- `examples/sync_web_search.py`

## License

MIT — see [LICENSE](LICENSE).
