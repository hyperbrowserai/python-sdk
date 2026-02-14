"""
Synchronous HyperAgent task example.

Run:
    export HYPERBROWSER_API_KEY="your_api_key"
    python3 examples/sync_hyper_agent_task.py
"""

from hyperbrowser import Hyperbrowser
from hyperbrowser.models.agents.hyper_agent import StartHyperAgentTaskParams


def main() -> None:
    with Hyperbrowser() as client:
        result = client.agents.hyper_agent.start_and_wait(
            StartHyperAgentTaskParams(
                task="Open https://example.com and summarize the page.",
                max_steps=4,
            )
        )
        print(f"Job status: {result.status}")
        print(f"Steps collected: {len(result.steps)}")


if __name__ == "__main__":
    main()
