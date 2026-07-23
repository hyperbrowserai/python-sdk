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

## Configuration

Both the sync and async client follow similar configuration params

### API Key
The API key can be configured either from the constructor arguments or environment variables using `HYPERBROWSER_API_KEY`

If no API key is provided, the client falls back to a saved OAuth session created by `hx auth login`. By default it reads `~/.hx_config/auth/default.json`, or `~/.hx_config/auth/<profile>.json` when `HYPERBROWSER_PROFILE` or `ClientConfig(profile=...)` is set.

Profile names must match `^[A-Za-z0-9._-]+$`.

`base_url` and `HYPERBROWSER_BASE_URL` accept either `https://host` or `https://host/api`. The client normalizes both to the same control-plane base URL.

## Usage

### Async

```python
import asyncio
from pyppeteer import connect
from hyperbrowser import AsyncHyperbrowser

HYPERBROWSER_API_KEY = "test-key"

async def main():
    async with AsyncHyperbrowser(api_key=HYPERBROWSER_API_KEY) as client:
        session = await client.sessions.create()

        ws_endpoint = session.ws_endpoint
        browser = await connect(browserWSEndpoint=ws_endpoint, defaultViewport=None)

        # Get pages
        pages = await browser.pages()
        if not pages:
            raise Exception("No pages available")

        page = pages[0]

        # Navigate to a website
        print("Navigating to Hacker News...")
        await page.goto("https://news.ycombinator.com/")
        page_title = await page.title()
        print("Page title:", page_title)

        await page.close()
        await browser.disconnect()
        await client.sessions.stop(session.id)
        print("Session completed!")

# Run the asyncio event loop
asyncio.get_event_loop().run_until_complete(main())
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

### Passing parameters

Every manager method that takes a params object accepts **either** a plain
dictionary (recommended — you get editor autocomplete via the `*Dict`
`TypedDict` types) **or** the existing Pydantic params class. Both produce
identical requests, so existing code keeps working after upgrading.

```python
from hyperbrowser import Hyperbrowser
from hyperbrowser.models import StartScrapeJobParams  # still supported

client = Hyperbrowser(api_key="test-key")

# New: plain dict with snake_case keys (autocompletes against StartScrapeJobParamsDict)
client.scrape.start_and_wait(
    {
        "url": "https://example.com",
        "scrape_options": {"formats": ["markdown"], "only_main_content": True},
    }
)

# Existing: Pydantic params object — unchanged
client.scrape.start_and_wait(
    StartScrapeJobParams(
        url="https://example.com",
        scrape_options={"formats": ["markdown"], "only_main_content": True},
    )
)
```

For extraction and structured web-fetch outputs, the `schema` field still
accepts a Pydantic model class or a raw JSON schema dict, exactly as before.

## Sandboxes

The sync and async clients expose the same sandbox APIs through `client.sandboxes`.

### Create a sandbox with pre-exposed ports

```python
from hyperbrowser import Hyperbrowser
from hyperbrowser.models import CreateSandboxParams, SandboxExposeParams

client = Hyperbrowser(api_key="test-key")
sandbox = client.sandboxes.create(
    CreateSandboxParams(
        image_name="node",
        cpu=4,
        memory_mib=4096,
        disk_mib=8192,
        exposed_ports=[SandboxExposeParams(port=3000, auth=True)],
    )
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
from hyperbrowser.models import CreateSandboxParams, CreateVolumeParams, SandboxVolumeMount

client = Hyperbrowser(api_key="test-key")

volume = client.volumes.create(CreateVolumeParams(name="project-cache"))
all_volumes = client.volumes.list()
same_volume = client.volumes.get(volume.id)

sandbox = client.sandboxes.create(
    CreateSandboxParams(
        image_name="node",
        mounts={
            "/workspace/cache": SandboxVolumeMount(
                id=same_volume.id,
                type="rw",
                shared=True,
            )
        },
    )
)

sandbox.stop()
client.close()
```

### List sandboxes with filters

```python
from hyperbrowser import Hyperbrowser
from hyperbrowser.models import SandboxListParams

client = Hyperbrowser(api_key="test-key")
result = client.sandboxes.list(
    SandboxListParams(
        status="active",
        search="sandbox",
        start=1711929600000,
        end=1712016000000,
        limit=20,
    )
)

for sandbox in result.sandboxes:
    print(sandbox.id, sandbox.status)
```

### List snapshots for a specific image

```python
from hyperbrowser import Hyperbrowser
from hyperbrowser.models import SandboxSnapshotListParams

client = Hyperbrowser(api_key="test-key")
snapshots = client.sandboxes.list_snapshots(
    SandboxSnapshotListParams(image_name="node", status="created", limit=10)
)
```

### Expose and unexpose ports

```python
from hyperbrowser import Hyperbrowser
from hyperbrowser.models import CreateSandboxParams, SandboxExposeParams

client = Hyperbrowser(api_key="test-key")
sandbox = client.sandboxes.create(
    CreateSandboxParams(
        image_name="node", cpu=2, memory_mib=2048, disk_mib=8192
    )
)

result = sandbox.expose(SandboxExposeParams(port=8080, auth=True))
print(result.url, result.browser_url)

sandbox.unexpose(8080)
```

### Batch file writes with per-file options

```python
from hyperbrowser import Hyperbrowser
from hyperbrowser.models import CreateSandboxParams, SandboxFileWriteEntry

client = Hyperbrowser(api_key="test-key")
sandbox = client.sandboxes.create(CreateSandboxParams(image_name="node"))

sandbox.files.write(
    [
        SandboxFileWriteEntry(
            path="/tmp/config.json",
            data='{"debug":true}\n',
            append=True,
            mode="600",
        ),
        SandboxFileWriteEntry(
            path="/tmp/blob.bin",
            data=b"\x00\x01\x02",
        ),
    ]
)
```

### Resume terminal output after reconnect

```python
from hyperbrowser import Hyperbrowser
from hyperbrowser.models import CreateSandboxParams, SandboxTerminalCreateParams

client = Hyperbrowser(api_key="test-key")
sandbox = client.sandboxes.create(CreateSandboxParams(image_name="node"))
terminal = sandbox.terminal.create(SandboxTerminalCreateParams(command="bash"))

connection = terminal.attach(cursor=10)
for event in connection.events():
    print(event)
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
