"""
Asynchronous scrape example.

Run:
    export HYPERBROWSER_API_KEY="your_api_key"
    python3 examples/async_scrape.py
"""

import asyncio

from hyperbrowser import AsyncHyperbrowser
from hyperbrowser.exceptions import HyperbrowserTimeoutError
from hyperbrowser.models import ScrapeOptions, StartScrapeJobParams


async def main() -> None:
    async with AsyncHyperbrowser() as client:
        try:
            result = await client.scrape.start_and_wait(
                StartScrapeJobParams(
                    url="https://hyperbrowser.ai",
                    scrape_options=ScrapeOptions(formats=["markdown"]),
                ),
                poll_interval_seconds=1.0,
                max_wait_seconds=120.0,
            )
        except HyperbrowserTimeoutError:
            print("Scrape job timed out.")
            return

        if result.data and result.data.markdown:
            print(result.data.markdown[:500])
        else:
            print(
                f"Scrape finished with status={result.status} and no markdown payload."
            )


if __name__ == "__main__":
    asyncio.run(main())
