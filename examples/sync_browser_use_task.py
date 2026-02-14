"""
Synchronous browser-use task example.

Run:
    export HYPERBROWSER_API_KEY="your_api_key"
    python3 examples/sync_browser_use_task.py
"""

from hyperbrowser import Hyperbrowser
from hyperbrowser.models.agents.browser_use import StartBrowserUseTaskParams


def main() -> None:
    with Hyperbrowser() as client:
        result = client.agents.browser_use.start_and_wait(
            StartBrowserUseTaskParams(
                task="Open https://example.com and return the page title.",
            )
        )
        print(f"Job status: {result.status}")
        if result.output is not None:
            print(f"Task output: {result.output}")


if __name__ == "__main__":
    main()
