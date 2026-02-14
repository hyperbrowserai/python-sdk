"""
Synchronous web crawl example.

Run:
    export HYPERBROWSER_API_KEY="your_api_key"
    python3 examples/sync_web_crawl.py
"""

from hyperbrowser import Hyperbrowser
from hyperbrowser.exceptions import HyperbrowserTimeoutError
from hyperbrowser.models import StartWebCrawlJobParams


def main() -> None:
    with Hyperbrowser() as client:
        try:
            result = client.web.crawl.start_and_wait(
                StartWebCrawlJobParams(
                    url="https://hyperbrowser.ai",
                ),
                poll_interval_seconds=1.0,
                max_wait_seconds=120.0,
            )
        except HyperbrowserTimeoutError:
            print("Web crawl job timed out.")
            return

        print(f"Status: {result.status}")
        print(f"Crawled pages in batch: {len(result.data or [])}")


if __name__ == "__main__":
    main()
