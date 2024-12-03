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

## Usage

### Async

```python
import asyncio
from pyppeteer import connect
from hyperbrowser.client.async_client import AsyncHyperbrowser as Hyperbrowser

HYPERBROWSER_API_KEY = "test-key"

async def main():
    client = Hyperbrowser(api_key=HYPERBROWSER_API_KEY)
    session = await client.create_session()

    ws_endpoint = f"{session.websocket_url}&apiKey={HYPERBROWSER_API_KEY}"
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
    print("Session completed!")

# Run the asyncio event loop
asyncio.get_event_loop().run_until_complete(main())
```
### Sync

```python
from playwright.sync_api import sync_playwright
from hyperbrowser.client.sync import Hyperbrowser

HYPERBROWSER_API_KEY = "test-key"

def main():
    client = Hyperbrowser(api_key=HYPERBROWSER_API_KEY)
    session = client.create_session()

    ws_endpoint = f"{session.websocket_url}&apiKey={HYPERBROWSER_API_KEY}"

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

# Run the asyncio event loop
main()
```