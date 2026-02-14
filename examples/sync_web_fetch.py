"""
Synchronous web fetch example.

Run:
    export HYPERBROWSER_API_KEY="your_api_key"
    python3 examples/sync_web_fetch.py
"""

from hyperbrowser import Hyperbrowser
from hyperbrowser.models import FetchParams


def main() -> None:
    with Hyperbrowser() as client:
        response = client.web.fetch(
            FetchParams(
                url="https://hyperbrowser.ai",
            )
        )

        print(f"Job ID: {response.job_id}")
        print(f"Status: {response.status}")
        if response.data and response.data.markdown:
            print(response.data.markdown[:500])


if __name__ == "__main__":
    main()
