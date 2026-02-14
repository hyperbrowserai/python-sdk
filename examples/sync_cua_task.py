"""
Synchronous CUA task example.

Run:
    export HYPERBROWSER_API_KEY="your_api_key"
    python3 examples/sync_cua_task.py
"""

from hyperbrowser import Hyperbrowser
from hyperbrowser.models.agents.cua import StartCuaTaskParams


def main() -> None:
    with Hyperbrowser() as client:
        result = client.agents.cua.start_and_wait(
            StartCuaTaskParams(
                task="Open https://example.com and summarize the page.",
                max_steps=4,
            )
        )
        print(f"Job status: {result.status}")
        print(f"Steps collected: {len(result.steps)}")


if __name__ == "__main__":
    main()
