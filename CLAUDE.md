# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the Hyperbrowser Python SDK - a client library for interacting with the Hyperbrowser API for cloud browser automation. It provides both synchronous (`Hyperbrowser`) and asynchronous (`AsyncHyperbrowser`) clients.

## Development Commands

```bash
# Install dependencies (uses Poetry)
poetry install

# Run linting with ruff
poetry run ruff check .

# Format code with ruff
poetry run ruff format .
```

## Architecture

### Client Structure

The SDK follows a dual sync/async pattern with mirrored implementations:

- **Entry Points**: `Hyperbrowser` (sync) and `AsyncHyperbrowser` (async) in `hyperbrowser/__init__.py`
- **Base Class**: `HyperbrowserBase` in `client/base.py` handles common config and URL building
- **Transport Layer**: `transport/` contains `SyncTransport` and `AsyncTransport` wrapping httpx clients

### Manager Pattern

Both clients expose identical APIs through manager classes that handle specific resource types:

```
client.sessions     # Browser session management
client.scrape       # Web scraping jobs
client.scrape.batch # Batch web scraping jobs
client.crawl        # Website crawling jobs
client.extract      # Data extraction jobs
client.web          # Web fetch/search operations
client.web.batch_fetch # Batch web fetch operations
client.agents       # AI agent integrations (browser_use, cua, claude_computer_use, hyper_agent, gemini_computer_use)
client.profiles     # Browser profile management
client.extensions   # Browser extension management
client.team         # Team/credit info
client.computer_action  # Low-level computer actions
```

Each manager lives in `client/managers/sync_manager/` or `client/managers/async_manager/` with identical method signatures.

### Models

All Pydantic models are in `hyperbrowser/models/`:
- Request params: `Start*Params`, `Create*Params`
- Response types: `*Response`, `*StatusResponse`
- Data models: `*Data`, `*TaskData`

Models are re-exported from `hyperbrowser/models/__init__.py` for easy importing.

### Pre-built Tools

`hyperbrowser/tools/` contains ready-to-use tool definitions for OpenAI and Anthropic function calling:
- `WebsiteScrapeTool`, `WebsiteScreenshotTool`, `WebsiteCrawlTool`, `WebsiteExtractTool`, `BrowserUseTool`
- Each has `openai_tool_definition`, `anthropic_tool_definition`, plus sync/async runnable methods

## Key Patterns

- **API Key**: Via constructor `api_key=` or `HYPERBROWSER_API_KEY` env var
- **Base URL**: Defaults to `https://api.hyperbrowser.ai`, configurable via `base_url=` or `HYPERBROWSER_BASE_URL`
- **Job Polling**: Managers provide `start_and_wait()` methods that poll until completion
- **Context Managers**: `AsyncHyperbrowser` supports `async with` for automatic cleanup
