"""
Asynchronous extract example.

Run:
    export HYPERBROWSER_API_KEY="your_api_key"
    python examples/async_extract.py
"""

import asyncio

from hyperbrowser import AsyncHyperbrowser
from hyperbrowser.models import StartExtractJobParams


async def main() -> None:
    async with AsyncHyperbrowser() as client:
        result = await client.extract.start_and_wait(
            StartExtractJobParams(
                urls=["https://hyperbrowser.ai"],
                prompt="Extract the main product value propositions as a list.",
            ),
            poll_interval_seconds=1.0,
            max_wait_seconds=120.0,
        )

        print(result.status)
        print(result.data)


if __name__ == "__main__":
    asyncio.run(main())
