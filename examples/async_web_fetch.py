"""
Asynchronous web fetch example.

Run:
    export HYPERBROWSER_API_KEY="your_api_key"
    python3 examples/async_web_fetch.py
"""

import asyncio

from hyperbrowser import AsyncHyperbrowser
from hyperbrowser.models import FetchParams


async def main() -> None:
    async with AsyncHyperbrowser() as client:
        response = await client.web.fetch(
            FetchParams(
                url="https://hyperbrowser.ai",
            )
        )

        print(f"Job ID: {response.job_id}")
        print(f"Status: {response.status}")
        if response.data and response.data.markdown:
            print(response.data.markdown[:500])


if __name__ == "__main__":
    asyncio.run(main())
