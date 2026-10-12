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
  and values of 1 byte to 32 KiB of UTF-8 without NUL bytes.
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
  For strict cancellation timing, use the async client: blocking DNS, custom
  transports or hooks, shared HTTP/2 control connections, and trickled headers
  on a reused control connection can delay cancellation in the sync client.
- A process start with secrets that times out raises an error with code
  `secret_process_outcome_unknown`: the command may be running, so check
  `sandbox.processes.list()` before retrying.

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
