"""
Example: asynchronous web search with the Hyperbrowser SDK.

Run:
    export HYPERBROWSER_API_KEY="your_api_key"
    python3 examples/async_web_search.py
"""

import asyncio

from hyperbrowser import AsyncHyperbrowser
from hyperbrowser.models import WebSearchParams


async def main() -> None:
    async with AsyncHyperbrowser() as client:
        response = await client.web.search(
            WebSearchParams(
                query="Hyperbrowser Python SDK",
                page=1,
            )
        )

        print(f"Job ID: {response.job_id}")
        print(f"Status: {response.status}")

        if not response.data:
            print("No results returned.")
            return

        print(f"Query: {response.data.query}")
        for index, result in enumerate(response.data.results[:5], start=1):
            print(f"{index}. {result.title} -> {result.url}")


if __name__ == "__main__":
    asyncio.run(main())
