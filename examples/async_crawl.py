"""
Asynchronous crawl example.

Run:
    export HYPERBROWSER_API_KEY="your_api_key"
    python3 examples/async_crawl.py
"""

import asyncio

from hyperbrowser import AsyncHyperbrowser
from hyperbrowser.exceptions import HyperbrowserTimeoutError
from hyperbrowser.models import StartCrawlJobParams


async def main() -> None:
    async with AsyncHyperbrowser() as client:
        try:
            result = await client.crawl.start_and_wait(
                StartCrawlJobParams(
                    url="https://hyperbrowser.ai",
                    max_pages=3,
                ),
                poll_interval_seconds=1.0,
                max_wait_seconds=120.0,
            )
        except HyperbrowserTimeoutError:
            print("Crawl job timed out.")
            return

        print(f"Status: {result.status}")
        print(f"Crawled pages in batch: {len(result.data)}")
        for page in result.data[:5]:
            print(f"- {page.url} ({page.status})")


if __name__ == "__main__":
    asyncio.run(main())
