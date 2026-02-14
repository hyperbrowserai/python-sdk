"""
Asynchronous web crawl example.

Run:
    export HYPERBROWSER_API_KEY="your_api_key"
    python3 examples/async_web_crawl.py
"""

import asyncio

from hyperbrowser import AsyncHyperbrowser
from hyperbrowser.exceptions import HyperbrowserTimeoutError
from hyperbrowser.models import StartWebCrawlJobParams


async def main() -> None:
    async with AsyncHyperbrowser() as client:
        try:
            result = await client.web.crawl.start_and_wait(
                StartWebCrawlJobParams(
                    url="https://hyperbrowser.ai",
                ),
                poll_interval_seconds=1.0,
                max_wait_seconds=120.0,
            )
        except HyperbrowserTimeoutError:
            print("Web crawl job timed out.")
            return

        print(f"Status: {result.status}")
        print(f"Crawled pages in batch: {len(result.data or [])}")


if __name__ == "__main__":
    asyncio.run(main())
