"""
Asynchronous team credit info example.

Run:
    export HYPERBROWSER_API_KEY="your_api_key"
    python3 examples/async_team_credit_info.py
"""

import asyncio

from hyperbrowser import AsyncHyperbrowser


async def main() -> None:
    async with AsyncHyperbrowser() as client:
        credit_info = await client.team.get_credit_info()
        print(f"Usage: {credit_info.usage}")
        print(f"Limit: {credit_info.limit}")
        print(f"Remaining: {credit_info.remaining}")


if __name__ == "__main__":
    asyncio.run(main())
