"""
Synchronous Gemini Computer Use task example.

Run:
    export HYPERBROWSER_API_KEY="your_api_key"
    python3 examples/sync_gemini_computer_use_task.py
"""

from hyperbrowser import Hyperbrowser
from hyperbrowser.models.agents.gemini_computer_use import (
    StartGeminiComputerUseTaskParams,
)


def main() -> None:
    with Hyperbrowser() as client:
        result = client.agents.gemini_computer_use.start_and_wait(
            StartGeminiComputerUseTaskParams(
                task="Open https://example.com and summarize the page.",
                max_steps=4,
            )
        )
        print(f"Job status: {result.status}")
        print(f"Steps collected: {len(result.steps)}")


if __name__ == "__main__":
    main()
