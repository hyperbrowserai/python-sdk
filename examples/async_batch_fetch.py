"""
Asynchronous batch fetch example.

Run:
    export HYPERBROWSER_API_KEY="your_api_key"
    python3 examples/async_batch_fetch.py
"""

import asyncio

from hyperbrowser import AsyncHyperbrowser
from hyperbrowser.exceptions import HyperbrowserTimeoutError
from hyperbrowser.models import StartBatchFetchJobParams


async def main() -> None:
    async with AsyncHyperbrowser() as client:
        try:
            result = await client.web.batch_fetch.start_and_wait(
                StartBatchFetchJobParams(
                    urls=[
                        "https://hyperbrowser.ai",
                        "https://docs.hyperbrowser.ai",
                    ],
                ),
                poll_interval_seconds=1.0,
                max_wait_seconds=120.0,
            )
        except HyperbrowserTimeoutError:
            print("Batch fetch job timed out.")
            return

        print(f"Status: {result.status}")
        print(f"Fetched pages: {len(result.data or [])}")


if __name__ == "__main__":
    asyncio.run(main())
