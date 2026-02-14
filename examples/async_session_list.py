"""
Example: list sessions asynchronously with the Hyperbrowser SDK.

Run:
    export HYPERBROWSER_API_KEY="your_api_key"
    python3 examples/async_session_list.py
"""

import asyncio

from hyperbrowser import AsyncHyperbrowser
from hyperbrowser.models import SessionListParams


async def main() -> None:
    async with AsyncHyperbrowser() as client:
        response = await client.sessions.list(
            SessionListParams(
                page=1,
                limit=5,
            )
        )

        print(f"Success: {response.success}")
        print(f"Returned sessions: {len(response.data)}")
        for session in response.data:
            print(f"- {session.id} ({session.status})")


if __name__ == "__main__":
    asyncio.run(main())
