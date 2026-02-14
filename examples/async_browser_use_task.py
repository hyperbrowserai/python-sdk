"""
Asynchronous browser-use task example.

Run:
    export HYPERBROWSER_API_KEY="your_api_key"
    python3 examples/async_browser_use_task.py
"""

import asyncio

from hyperbrowser import AsyncHyperbrowser
from hyperbrowser.models.agents.browser_use import StartBrowserUseTaskParams


async def main() -> None:
    async with AsyncHyperbrowser() as client:
        result = await client.agents.browser_use.start_and_wait(
            StartBrowserUseTaskParams(
                task="Open https://example.com and return the page title.",
            )
        )
        print(f"Job status: {result.status}")
        if result.output is not None:
            print(f"Task output: {result.output}")


if __name__ == "__main__":
    asyncio.run(main())
