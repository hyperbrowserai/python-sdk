"""
Asynchronous computer action example.

Run:
    export HYPERBROWSER_API_KEY="your_api_key"
    export HYPERBROWSER_SESSION_ID="session_id"
    python3 examples/async_computer_action.py
"""

import asyncio
import os

from hyperbrowser import AsyncHyperbrowser
from hyperbrowser.exceptions import HyperbrowserError


async def main() -> None:
    session_id = os.getenv("HYPERBROWSER_SESSION_ID")
    if session_id is None:
        raise HyperbrowserError("Set HYPERBROWSER_SESSION_ID before running")

    async with AsyncHyperbrowser() as client:
        response = await client.computer_action.screenshot(session_id)
        print(f"Action successful: {response.success}")


if __name__ == "__main__":
    asyncio.run(main())
