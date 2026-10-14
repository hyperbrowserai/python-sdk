# Hyperbrowser Python SDK

Checkout the full documentation [here](https://hyperbrowser.ai/docs)

## Installation

Currently Hyperbrowser supports creating a browser session in two ways:

- Async Client
- Sync Client

It can be installed from `pypi` by running :

```shell
pip install hyperbrowser
```

The browser-control examples below also use Playwright:

```shell
pip install playwright
```

## Configuration

Both the sync and async client follow similar configuration params

### API Key
The API key can be configured either from the constructor arguments or environment variables using `HYPERBROWSER_API_KEY`

If no API key is provided, the client falls back to a saved OAuth session created by `hx auth login`. By default it reads `~/.hx_config/auth/default.json`, or `~/.hx_config/auth/<profile>.json` when `HYPERBROWSER_PROFILE` or `ClientConfig(profile=...)` is set.

Profile names must match `^[A-Za-z0-9._-]+$`.

`base_url` and `HYPERBROWSER_BASE_URL` accept either `https://host` or `https://host/api`. The client normalizes both to the same control-plane base URL.

## WebMCP page tools

Create a session with `{"enable_web_mcp": True}` (default: false), then navigate
to a page that exposes WebMCP tools using Playwright. With that session open:

```python
discovery = client.sessions.webmcp.list_tools(session.id)
# Select a tool using its name, source page/frame, and input schema.
tool = next(tool for tool in discovery.tools if tool.name == "search")
result = client.sessions.webmcp.invoke(session.id, {
    "tool_ref": tool.tool_ref,
    "input": {"query": "flights to Tokyo"},  # Match the selected tool's schema.
})
print(result.status, result.output)
```

For long-running tools or forms awaiting human submission, use
`client.sessions.webmcp.start(session_id, params)`, then
`client.sessions.webmcp.get_result(session_id, invocation_id, {"wait_seconds": 30})`
until the status is terminal. `client.sessions.webmcp.cancel(session_id, invocation_id)`
requests best-effort cancellation. Blocking invocation defaults to 60 seconds
(maximum 120); `start` defaults to 300 seconds (maximum 3,600) via `timeout_seconds`.
All five methods also work with `AsyncHyperbrowser` by adding `await`.

Discover tools again after navigation. Invocations never automatically retry;
losing a response can leave an unknown outcome. Handles are ephemeral and
terminal results expire after 10 minutes or earlier eviction. Check result
status and truncation metadata before using output. Tool input and output keys
are not renamed. Request TypedDicts are available in `hyperbrowser.types`, and
Pydantic request/response models in `hyperbrowser.models`.

See the [WebMCP guide](https://hyperbrowser.ai/docs/sessions/webmcp) for complete
examples, cancellation behavior, human submission, and limits.

## Web Bot Auth

A session can sign its requests with Web Bot Auth so websites can verify that they
come from Hyperbrowser. Web Bot Auth is enabled for teams on request.

```python
session = client.sessions.create({"web_bot_auth": True})
print(session.launch_state.web_bot_auth.signature_agent)  # https://www.hyperbrowser.ai

# Sign only requests to these hosts and their subdomains:
client.sessions.create({"web_bot_auth": {"only_domains": ["example.com"]}})
```

Agent tasks accept `web_bot_auth` in `session_options`; scrape, crawl, and extract
jobs do not. It cannot be combined with `use_ultra_stealth` or
`start_from_snapshot`. See the
[Web Bot Auth guide](https://hyperbrowser.ai/docs/sessions/web-bot-auth).

## Proxy routes

`proxy_routes` sends some hosts' traffic straight out instead of through the
session's proxy, or the other way round. The first route that matches a host
decides; hosts that no route matches use the proxy. Proxy routes require
`use_proxy` and are enabled for teams on request.

```python
session = client.sessions.create({
    "use_proxy": True,
    "proxy_routes": [
        {"match": "api.example.com", "proxy": "default"},  # stays on the proxy
        {"match": ["*.example.com", "cdn.example.net"], "proxy": "direct"},
    ],
})
```

A pattern is a hostname, `*.example.com` (its subdomains, not `example.com`
itself), or `*` (every host). Proxy routes only apply to `client.sessions.create`
and cannot be combined with `allow_internet_access=False`, `allow_out`, or
`deny_out`. See the
[proxy routes guide](https://hyperbrowser.ai/docs/sessions/proxy-routes).

## Fill credentials into browser sessions

A credential is a secret of type `"credential"` that holds a website login,
such as a username and password. Its value is encrypted on your machine like
any other secret value, and the platform types it into pages of a browser
session; after upload, neither the API, your code, nor an LLM sees it again.

```python
from playwright.sync_api import sync_playwright

from hyperbrowser import Hyperbrowser

client = Hyperbrowser(api_key="test-key")

# Field names (here "username" and "password") are what a fill refers to.
client.secrets.create_credential(
    "github",
    {"username": "ada@example.com", "password": "correct horse battery staple"},
    allowed_origins=["https://github.com"],
    description="GitHub login",
)

# Credentials can only be attached when the session is created.
session = client.sessions.create({"credentials": ["github"]})

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp(session.ws_endpoint)
    page = browser.contexts[0].pages[0]
    page.goto("https://github.com/login")

    result = client.sessions.credentials.fill(
        session.id,
        {
            "credential": "github",
            "fields": [
                {"field": "username", "selector": "#login_field"},
                {"field": "password", "selector": "#password"},
            ],
        },
    )
    if all(field.outcome == "filled" for field in result.fields):
        # Fill only types. Submitting is up to you.
        page.click("input[type=submit]")

client.sessions.stop(session.id)
```

`fill()` returns the filled page's `page_id` and `origin`, the credential
`version`, and an outcome per field. Values are never returned.

| Outcome | Meaning |
| --- | --- |
| `filled` | The input now holds exactly the stored value. |
| `not_found` | No input matched the selector. |
| `ambiguous` | Several visible inputs matched the selector. |
| `not_editable` | The input is disabled, read-only, hidden, or not a text input. |
| `not_accepted` | The page didn't keep the value, for example because of `maxlength`. |
| `not_populated` | The stored credential has no such field. |

Things to know:

- A credential can be filled only on its allowed origins
  (`scheme://host[:port]`; `https://*.example.com` matches any subdomain but
  not `example.com` itself). Change them with
  `client.secrets.set_allowed_origins("github", [...])`; `None` clears them,
  after which the credential can't be filled. `client.secrets.update()` takes
  `{"metadata": {"browser": None}}` too: each metadata member sent replaces the
  stored one and `None` removes it.
- Credential values map 1-64 character field names (letters, digits, `_`, `.`
  and `-`) to non-empty strings, up to 32 KiB of JSON in total. They are
  checked before anything is sent; rotate one with
  `client.secrets.add_version("github", {...})`. `client.secrets.list({"type":
  "credential"})` lists only credentials.
- A fill takes 1-16 fields, each at most once. Without `page_id` it picks the
  only tab, else the single tab on an allowed origin, else the single visible
  tab. Under Playwright every tab reports as visible, so with several tabs on
  allowed origins pass the tab's CDP target ID as `page_id`:
  `page.context.new_cdp_session(page).send("Target.getTargetInfo")["targetInfo"]["targetId"]`.
  For a login form in an iframe, pass `"frame": {"url": "https://login.example.com/"}`
  (a URL prefix).
- Fill is safe to retry and never retried automatically. It waits at least
  30 seconds for the API (the client timeout when longer).
- Attaching credentials needs an API key with `secrets.use`; filling also needs
  `browser.sessions.update`. The team needs the secrets feature. Sessions with
  credentials run as Firecracker browsers with Chrome's password manager off.
- Fills are recorded in the session's event log as `credential_filled` and
  `credential_fill_refused`.
- Errors are raised as `HyperbrowserError` with the API's `code`, `retryable`,
  and `status_code`. `details` holds the API's response body, so the
  candidate tabs of an ambiguous fill are in `error.details["details"]["pages"]`
  (each with `pageId`, `url` and `title`). Error codes from the API:
  - `CREDENTIAL_PAGE_AMBIGUOUS` (409): several tabs could be the target; pass
    one's `pageId` as `page_id`. `CREDENTIAL_FRAME_AMBIGUOUS` (409) is the same
    for frames.
  - `CREDENTIAL_ORIGIN_NOT_ALLOWED` (403): the page's origin (in `details`)
    isn't allowed; nothing was typed.
  - `CREDENTIAL_NOT_ATTACHED` (403): the credential wasn't attached when the
    session was created.
  - `CREDENTIAL_NOT_READY` (409): the credential has no allowed origins or no
    value.
  - `CREDENTIAL_PAGE_NOT_FOUND`, `CREDENTIAL_FRAME_NOT_FOUND` (404),
    `SECRET_NOT_FOUND` (404), `SECRET_TYPE_MISMATCH` (409, a plain secret was
    named), `SESSION_NOT_ACTIVE` (409).
  - `CREDENTIAL_FILL_TIMEOUT` (503/504, retryable) and
    `CREDENTIAL_FILL_FAILED` (500/502, retryable as flagged).
  - `CREDENTIALS_UNSUPPORTED_RUNTIME` (400) and `CREDENTIAL_FILL_UNSUPPORTED`
    (501): the session's browser can't fill credentials.
  - Locally, invalid fill requests raise `invalid_request` and invalid values
    raise `invalid_secret_value`, before any request.

### Use with LLM SDKs

`CredentialFillTool` lets a model fill a credential by name while your
application binds the session ID. The model chooses only the credential, the
fields with their CSS selectors, and optionally a `page_id` or `frame_url`; it
never sees the values. `runnable()` returns JSON text for the model: the fill
result, or `{"error": {"code", "message", "retryable", "details"}}` when the
fill fails, so the model can react (for example by choosing a `page_id`).
Give the model your other browser tools too, since it must submit the form
itself. `async_runnable()` does the same with `AsyncHyperbrowser`.

OpenAI (Chat Completions):

```python
import json

from openai import OpenAI

from hyperbrowser.tools import CredentialFillTool

openai_client = OpenAI()
tools = [CredentialFillTool.openai_tool_definition]  # plus your browser tools
messages = [{"role": "user", "content": "Sign in to GitHub with the credential named github."}]
while True:
    response = openai_client.chat.completions.create(
        model="gpt-5", messages=messages, tools=tools
    )
    message = response.choices[0].message
    messages.append(message)
    if not message.tool_calls:
        break
    for call in message.tool_calls:
        if call.function.name == "fill_credential":
            output = CredentialFillTool.runnable(
                client, session.id, json.loads(call.function.arguments)
            )
        else:
            output = run_browser_tool(call)  # your click/press/navigate tools
        messages.append({"role": "tool", "tool_call_id": call.id, "content": output})
```

Anthropic (Messages):

```python
import anthropic

from hyperbrowser.tools import CredentialFillTool

anthropic_client = anthropic.Anthropic()
tools = [CredentialFillTool.anthropic_tool_definition]  # plus your browser tools
messages = [{"role": "user", "content": "Sign in to GitHub with the credential named github."}]
while True:
    response = anthropic_client.messages.create(
        model="claude-sonnet-5-5", max_tokens=1024, tools=tools, messages=messages
    )
    messages.append({"role": "assistant", "content": response.content})
    if response.stop_reason != "tool_use":
        break
    results = []
    for block in response.content:
        if block.type != "tool_use":
            continue
        if block.name == "fill_credential":
            output = CredentialFillTool.runnable(client, session.id, block.input)
        else:
            output = run_browser_tool(block)
        results.append({"type": "tool_result", "tool_use_id": block.id, "content": output})
    messages.append({"role": "user", "content": results})
```

Gemini (google-genai):

```python
from google import genai
from google.genai import types

from hyperbrowser.tools import CredentialFillTool

gemini = genai.Client()
config = types.GenerateContentConfig(
    tools=[
        types.Tool(function_declarations=[CredentialFillTool.gemini_tool_definition])
    ]  # plus your browser tools
)
contents = [
    types.Content(
        role="user",
        parts=[types.Part.from_text(text="Sign in to GitHub with the credential named github.")],
    )
]
while True:
    response = gemini.models.generate_content(
        model="gemini-3.5-flash", contents=contents, config=config
    )
    contents.append(response.candidates[0].content)
    if not response.function_calls:
        break
    parts = []
    for call in response.function_calls:
        if call.name == "fill_credential":
            output = CredentialFillTool.runnable(client, session.id, call.args or {})
        else:
            output = run_browser_tool(call)
        parts.append(
            types.Part.from_function_response(name=call.name, response={"result": output})
        )
    contents.append(types.Content(role="user", parts=parts))
```

## Tools for LLM function calling

`hyperbrowser.tools` has ready-made tools: `WebsiteScrapeTool`,
`WebsiteScreenshotTool`, `WebsiteCrawlTool`, `WebsiteExtractTool`,
`BrowserUseTool` and `CredentialFillTool`. Each has `openai_tool_definition`
(a strict Chat Completions function tool), `anthropic_tool_definition`,
`gemini_tool_definition` (a function declaration dict for google-genai), and
`runnable()` / `async_runnable()` to run the model's input and return text for
the model.

## Usage

Hyperbrowser 1.0 accepts plain dictionaries for request parameters. Method
signatures use `TypedDict` definitions, so editors can autocomplete keys at
every nested level:

```python
from hyperbrowser import Hyperbrowser

client = Hyperbrowser(api_key="test-key")

# Preferred in 1.0: autocomplete works directly in the dictionary.
session = client.sessions.create(
    {
        "use_stealth": True,
        "screen": {"width": 1920, "height": 1080},
    }
)
```

Browser sessions can also use an outbound network policy. Omitting these fields
keeps the default unrestricted behavior:

```python
session = client.sessions.create(
    {
        "allow_internet_access": False,
        "allow_out": ["example.com"],
        "deny_out": ["0.0.0.0/0"],
    }
)
```

Direct browser policies accept domains, IPv4 addresses, and CIDR ranges in
`allow_out`; `deny_out` accepts IPv4 addresses and CIDR ranges. With a proxy,
allow rules must be domains and the only supported deny rule is `0.0.0.0/0`.

Existing Pydantic request classes remain accepted, so upgrading does not require
an immediate rewrite:

```python
from hyperbrowser.models import CreateSessionParams, ScreenConfig

session = client.sessions.create(
    CreateSessionParams(
        use_stealth=True,
        screen=ScreenConfig(width=1920, height=1080),
    )
)
```

Import request annotations from `hyperbrowser.types` when a named variable is
useful. The same names under `hyperbrowser.models` refer to the legacy Pydantic
request classes. Responses remain Pydantic models.

JSON Schema fields accept raw schema values, including object schemas with
`$defs`, `$ref`, or custom keywords, and boolean schemas where the API supports
them. Those schemas and other user-owned mappings are preserved as data; only
SDK-owned request keys are translated to their API aliases. Schema fields
documented as accepting a model class can also generate a schema from a Pydantic
model.

See the
[Hyperbrowser Python SDK 1.0 migration guide](https://hyperbrowser.ai/docs/sdks/python-1-0-migration)
for the complete compatibility details and migration checklist.

### Async

```python
import asyncio
from hyperbrowser import AsyncHyperbrowser
from playwright.async_api import async_playwright

HYPERBROWSER_API_KEY = "test-key"

async def main():
    async with AsyncHyperbrowser(api_key=HYPERBROWSER_API_KEY) as client:
        session = await client.sessions.create()

        try:
            async with async_playwright() as playwright:
                browser = await playwright.chromium.connect_over_cdp(
                    session.ws_endpoint
                )
                context = browser.contexts[0]
                page = context.pages[0]

                print("Navigating to Hacker News...")
                await page.goto("https://news.ycombinator.com/")
                print("Page title:", await page.title())
        finally:
            await client.sessions.stop(session.id)

# Run the asyncio event loop
asyncio.run(main())
```
### Sync

```python
from playwright.sync_api import sync_playwright
from hyperbrowser import Hyperbrowser

HYPERBROWSER_API_KEY = "test-key"

def main():
    client = Hyperbrowser(api_key=HYPERBROWSER_API_KEY)
    session = client.sessions.create()

    ws_endpoint = session.ws_endpoint

    # Launch Playwright and connect to the remote browser
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(ws_endpoint)
        context = browser.new_context()
        
        # Get the first page or create a new one
        if len(context.pages) == 0:
            page = context.new_page()
        else:
            page = context.pages[0]
        
        # Navigate to a website
        print("Navigating to Hacker News...")
        page.goto("https://news.ycombinator.com/")
        page_title = page.title()
        print("Page title:", page_title)
        
        page.close()
        browser.close()
        print("Session completed!")
    client.sessions.stop(session.id)

# Run the asyncio event loop
main()
```

## Sandboxes

The sync and async clients expose the same sandbox APIs through `client.sandboxes`.

### Create a sandbox with pre-exposed ports

```python
from hyperbrowser import Hyperbrowser

client = Hyperbrowser(api_key="test-key")
sandbox = client.sandboxes.create(
    {
        "image_name": "node",
        "cpu": 2,
        "memory_mib": 2048,
        "disk_mib": 8192,
        "exposed_ports": [{"port": 3000, "auth": True}],
    }
)

print(sandbox.exposed_ports[0].browser_url)
print(sandbox.cpu, sandbox.memory_mib, sandbox.disk_mib)
sandbox.stop()
client.close()
```

`cpu`, `memory_mib`, and `disk_mib` are only supported for image launches.

### Manage volumes and mount them in a sandbox

```python
from hyperbrowser import Hyperbrowser

client = Hyperbrowser(api_key="test-key")

volume = client.volumes.create({"name": "project-cache"})
all_volumes = client.volumes.list()
same_volume = client.volumes.get(volume.id)

sandbox = client.sandboxes.create(
    {
        "image_name": "node",
        "mounts": {
            "/workspace/cache": {
                "id": same_volume.id,
                "type": "rw",
                "shared": True,
            }
        },
    }
)

sandbox.stop()
client.volumes.delete(same_volume.id)
client.close()
```

### Manage secrets and pass them to sandbox processes

Secrets hold values such as API keys for sandbox processes. Values are
encrypted on your machine to the platform's public key before upload, and the
API never returns them. Methods that take a secret accept its ID or exact name.

```python
from pathlib import Path

from hyperbrowser import Hyperbrowser

client = Hyperbrowser(api_key="test-key")

# Values are str or bytes and are stored byte-for-byte, trailing newlines included.
client.secrets.create(
    {
        "name": "provider-key",
        "description": "Provider API key",
        "value": Path("provider-key.txt").read_bytes(),
    }
)
client.secrets.add_version("provider-key", "rotated-value")  # becomes version 2
detail = client.secrets.get("provider-key")  # metadata and versions, never the value
client.secrets.list({"search": "provider"})

sandbox = client.sandboxes.create(
    {
        "image_name": "node",
        # Delivered to the image's startup command (image launches only).
        "secrets": {"API_KEY": "provider-key"},
    }
)

# A plain name uses the latest version; {"name": ..., "version": N} pins one.
result = sandbox.exec(
    "node app.js",
    secrets={"API_KEY": {"name": "provider-key", "version": 2}},
)
process = sandbox.processes.start("node worker.js", secrets={"API_KEY": "provider-key"})
print(process.secrets)  # the version each variable received

client.secrets.delete_version("provider-key", 1)
client.secrets.delete("provider-key")
client.close()
```

Things to know:

- A secret is set only in the environment of the process it was passed to.
  Anything else running as the same user, or as root, in the sandbox can read
  that environment.
- A sandbox that has received secrets, and snapshots taken of it, report
  `contains_secrets=True`. Restoring such a snapshot needs the same access as
  passing secrets.
- Deleting a secret or version doesn't revoke a value already delivered to a
  sandbox.
- Limits: 100 secrets per team, 10 versions per secret, 32 secrets per process,
  and values of 1 byte to 32 KiB of UTF-8 without NUL bytes. Names are 1-128
  letters, digits, `_` or `-`, starting with a letter or digit.
- Reading secrets needs `secrets.read`; delivering them to a sandbox needs
  `secrets.use`. Creating a secret needs `secrets.manage`. Updating, rotating,
  and deleting secrets or versions through the SDK need both `secrets.read`
  and `secrets.manage`, since it resolves IDs and names through metadata reads.
  `add_version()` also reads the secret's `encryptionContext` to encrypt its
  value. The team needs the secrets feature.
- Secret-started process handles wait indefinitely by default with `wait()` or
  `result()`. A positive `wait(timeout_ms=...)` or `wait(timeout_sec=...)` limits
  the total local wait and raises `TimeoutError` (`asyncio.TimeoutError` for
  async handles); the process continues and the handle can be used to wait
  again. The start's timeout limits the command's execution separately.
  The sync client checks the limit between requests and caps each request's
  HTTP timeouts at the time left, so a slow response or a runtime token
  refresh can overrun it; use the async client for a strict limit.
  Secret process output comes from the receiver's retained output, so
  `max_output_bytes` does not apply; incomplete retained output raises an error.
- A process start with secrets that times out, or whose result the API can't
  confirm, raises a non-retryable error with code
  `secret_process_outcome_unknown`: the command may be running, so check
  `sandbox.processes.list()` before retrying. When the API reported the
  unknown outcome itself, its response body, including its own code
  (`SECRET_PROCESS_OUTCOME_UNKNOWN`), is in the error's `details`.
- `client.sandboxes.create()` with `secrets` raises the same
  `secret_process_outcome_unknown` error when the create may have reached the
  API but its result is unknown (a timeout, a dropped connection, or an
  unreadable response): a sandbox may be running its startup command with the
  secrets, so list sandboxes before retrying.
- Error codes from the API:
  - `SECRETS_ADMIN_REQUIRED` (403): the request used an `hx auth login`
    session of a team member who isn't an owner or admin. API keys are
    governed by their scopes instead.
  - `SECRETS_FEATURE_DISABLED` (403): the team doesn't have the secrets
    feature.
  - `SECRETS_NOT_CONFIGURED` (503): the platform has no secrets key
    configured. It isn't retried.
  - `SECRET_STARTUP_UNSUPPORTED` (400): the image has no startup command to
    deliver `secrets` to. Create the sandbox without them, then pass them to
    `sandbox.exec()` or `sandbox.processes.start()`.

### List sandboxes with filters

```python
from hyperbrowser import Hyperbrowser

client = Hyperbrowser(api_key="test-key")
result = client.sandboxes.list(
    {
        "status": "active",
        "search": "sandbox",
        "start": 1711929600000,
        "end": 1712016000000,
        "limit": 20,
    }
)

for sandbox in result.sandboxes:
    print(sandbox.id, sandbox.status)
```

### List snapshots for a specific image

```python
from hyperbrowser import Hyperbrowser

client = Hyperbrowser(api_key="test-key")
snapshots = client.sandboxes.list_snapshots(
    {"image_name": "node", "status": "created", "limit": 10}
)
```

### Expose and unexpose ports

```python
from hyperbrowser import Hyperbrowser

client = Hyperbrowser(api_key="test-key")
sandbox = client.sandboxes.create(
    {"image_name": "node", "cpu": 2, "memory_mib": 2048, "disk_mib": 8192}
)

result = sandbox.expose({"port": 8080, "auth": True})
print(result.url, result.browser_url)

sandbox.unexpose(8080)
```

### Batch file writes with per-file options

```python
from hyperbrowser import Hyperbrowser

client = Hyperbrowser(api_key="test-key")
sandbox = client.sandboxes.create({"image_name": "node"})

sandbox.files.write(
    [
        {
            "path": "/tmp/config.json",
            "data": '{"debug":true}\n',
            "append": True,
            "mode": "600",
        },
        {"path": "/tmp/blob.bin", "data": b"\x00\x01\x02"},
    ]
)
```

### Run commands and collect output

`sandbox.exec()` and `sandbox.processes.start()` stream command output from the
receiver as soon as execution starts. The SDK collects stdout and stderr in
memory, so a completed result is not limited to the receiver's replay buffer.
This requires a receiver supporting streaming `POST /sandbox/processes`; roll
out the receiver before upgrading the SDK.

```python
result = sandbox.exec("make test", max_output_bytes=128 * 1024 * 1024)
print(result.stdout, result.stderr, result.exit_code)

process = sandbox.processes.start("make test")
try:
    for event in process.stream():
        if event.type == "stdout":
            print(event.data, end="")
    result = process.wait()
finally:
    process.disconnect()
```

The combined output limit defaults to 64 MiB per command and can be adjusted
with `max_output_bytes`. Exceeding it raises `output_limit_exceeded`. A broken
stream, missing output, or receiver truncation raises `incomplete_output`.
These errors include the process ID and do not automatically rerun the command.

Process streams use a separate 60-second read-idle timeout once response headers
arrive. Output and the receiver's 15-second heartbeats reset this timeout, so quiet
commands can run longer than the client's ordinary HTTP timeout. That ordinary
timeout still applies to connection setup and waiting for response headers.

`start()` returns after the process starts and collects in the background.
`wait(timeout_sec=...)` limits the local wait; collection continues after a wait
timeout. The timeout passed to `start()` or `exec()` limits command execution.
A local wait timeout raises `TimeoutError` (`asyncio.TimeoutError` in the async API).
`disconnect()` stops collection and leaves the command running. Use `kill()` to
stop it. Reattaching with `get()` can retrieve only retained receiver output;
`wait()` raises if that output has been truncated.

The async API has the same behavior: await `exec()`, `start()`, `wait()`, and
`disconnect()`, and use `async for` with `stream()`.

### Resume terminal output after reconnect

```python
from hyperbrowser import Hyperbrowser

client = Hyperbrowser(api_key="test-key")
sandbox = client.sandboxes.create({"image_name": "node"})
terminal = sandbox.terminal.create({"command": "bash"})

connection = terminal.attach(cursor=10)
for event in connection.events():
    print(event)
```

### Cache remote Dockerfile builds

Use the public context fingerprint when deriving a cache name. It uses the same
Dockerfile source selection and `.dockerignore` rules as remote packaging,
including file contents, modes, paths, and symlinks. It ignores timestamps and
does not compress or stage the context on disk.

```python
from hyperbrowser.build_context import docker_build_context_fingerprint

fingerprint = docker_build_context_fingerprint("./app")
# Include build options such as platform and image_init in your cache key too.
image_name = f"app-{fingerprint[:32]}"
build = client.sandboxes.build_image_from_dockerfile(
    context_path="./app",
    image_name=image_name,
    expected_context_fingerprint=fingerprint,
)
```

If the archived inputs differ from the fingerprint, the SDK raises
`DockerBuildContextChangedError` before creating or uploading a build. Compute a
fresh fingerprint and repeat the lookup/build operation. Use the same `dockerfile`
and `force_full_context` selection when fingerprinting and building (the latter
is named `remote_full_context` on the build method). The expected fingerprint is
supported only for remote builds.

Fingerprinting streams included files and performs blocking I/O. Async callers
should use `await asyncio.to_thread(docker_build_context_fingerprint, "./app")`
(Python 3.9+) or an executor. It does not resolve mutable base-image tags or
network resources fetched by a Dockerfile; rebuild explicitly when those change.

Image listings distinguish `ready` from `uploaded`: a completed team image can
be ready to launch before its durability backup is uploaded. `ready` is `None`
when talking to an older server. Keep the returned image ID to pin that revision.

### Reuse an image or join a build

`get_or_build_image` provides the same operation on sync and async clients. Give
it either a remote Dockerfile context or a local Docker image. It derives a name
from the input identity and image initialization options, reuses a ready team
image, or submits a build and joins a compatible concurrent build automatically.
The optional prefix is a namespace, not a fixed image alias: different inputs
produce different names under the same prefix.

```python
resolved = client.sandboxes.get_or_build_image(
    context_path="./app",  # alternatively: docker_image="local/app:latest"
    image_name_prefix="my-app",
    wait_timeout=3600,
)
print(resolved.outcome)  # "reused", "joined", or "created"
sandbox = client.sandboxes.create({
    "image_name": resolved.image_name,
    "image_id": resolved.image_id,
})
```

With `wait=False`, a submitted/joined build is returned as `resolved.build`;
`image_id` is populated only when ready. `find_ready_image(name)` exposes the
exact-name lookup separately. Older servers fall back to uploaded-image reuse.
The public `hyperbrowser.image_builds.image_build_name` helper lets integrations
derive the same name from an existing context fingerprint or Docker image digest.
Passing `expected_context_fingerprint` or `expected_image_digest` avoids repeating
identity discovery; supply a fresh identity for each resolution request. Changes
between identity discovery and packaging are rejected instead of published under
the wrong name. Local Docker images must already be available in the daemon.

Automatic local-image identity discovery requires a Docker CLI and Engine
supporting **API 1.49 or newer (Docker 28.1+)** for platform-specific inspection.
Upgrade Docker and check for an older `DOCKER_API_VERSION` override if the helper
reports this requirement. Remote Dockerfile builds do not require local Docker.
The existing explicit-name import method retains its inspection fallback.

`force_build=True` skips ready-image lookup but still joins matching active builds
and permits existing layer/artifact caches. Use it to refresh mutable base tags or
external Dockerfile downloads. Joining does not change an existing builder's
resources. Lookup and creation use separate API calls; if another build completes
between them, an additional revision can be submitted.

Each caller owns its polling timeout. Canceling that wait does not cancel an
accepted backend build. Uploads have a separate inactivity allowance
(`upload_timeout=600` by default), not a total upload-duration limit. The existing
`build_image_from_dockerfile` and `build_image_from_docker_image` methods retain
their explicit-name behavior and continue to report build conflicts directly.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
