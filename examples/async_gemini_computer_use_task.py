"""
Asynchronous Gemini Computer Use task example.

Run:
    export HYPERBROWSER_API_KEY="your_api_key"
    python3 examples/async_gemini_computer_use_task.py
"""

import asyncio

from hyperbrowser import AsyncHyperbrowser
from hyperbrowser.models.agents.gemini_computer_use import (
    StartGeminiComputerUseTaskParams,
)


async def main() -> None:
    async with AsyncHyperbrowser() as client:
        result = await client.agents.gemini_computer_use.start_and_wait(
            StartGeminiComputerUseTaskParams(
                task="Open https://example.com and summarize the page.",
                max_steps=4,
            )
        )
        print(f"Job status: {result.status}")
        print(f"Steps collected: {len(result.steps)}")


if __name__ == "__main__":
    asyncio.run(main())
