"""
Synchronous extract example.

Run:
    export HYPERBROWSER_API_KEY="your_api_key"
    python3 examples/sync_extract.py
"""

from hyperbrowser import Hyperbrowser
from hyperbrowser.models import StartExtractJobParams


def main() -> None:
    with Hyperbrowser() as client:
        result = client.extract.start_and_wait(
            StartExtractJobParams(
                urls=["https://hyperbrowser.ai"],
                prompt="Extract the main product value propositions as a list.",
            ),
            poll_interval_seconds=1.0,
            max_wait_seconds=120.0,
        )

        print(result.status)
        print(result.data)


if __name__ == "__main__":
    main()
