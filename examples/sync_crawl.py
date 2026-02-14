"""
Synchronous crawl example.

Run:
    export HYPERBROWSER_API_KEY="your_api_key"
    python3 examples/sync_crawl.py
"""

from hyperbrowser import Hyperbrowser
from hyperbrowser.exceptions import HyperbrowserTimeoutError
from hyperbrowser.models import StartCrawlJobParams


def main() -> None:
    with Hyperbrowser() as client:
        try:
            result = client.crawl.start_and_wait(
                StartCrawlJobParams(
                    url="https://hyperbrowser.ai",
                    max_pages=3,
                ),
                poll_interval_seconds=1.0,
                max_wait_seconds=120.0,
            )
        except HyperbrowserTimeoutError:
            print("Crawl job timed out.")
            return

        print(f"Status: {result.status}")
        print(f"Crawled pages in batch: {len(result.data)}")
        for page in result.data[:5]:
            print(f"- {page.url} ({page.status})")


if __name__ == "__main__":
    main()
