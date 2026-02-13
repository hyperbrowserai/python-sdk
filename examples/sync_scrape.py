"""
Synchronous scrape example.

Run:
    export HYPERBROWSER_API_KEY="your_api_key"
    python examples/sync_scrape.py
"""

from hyperbrowser import Hyperbrowser
from hyperbrowser.exceptions import HyperbrowserTimeoutError
from hyperbrowser.models import ScrapeOptions, StartScrapeJobParams


def main() -> None:
    with Hyperbrowser() as client:
        try:
            result = client.scrape.start_and_wait(
                StartScrapeJobParams(
                    url="https://hyperbrowser.ai",
                    scrape_options=ScrapeOptions(formats=["markdown"]),
                ),
                poll_interval_seconds=1.0,
                max_wait_seconds=120.0,
            )
        except HyperbrowserTimeoutError:
            print("Scrape job timed out.")
            return

        if result.data and result.data.markdown:
            print(result.data.markdown[:500])
        else:
            print(
                f"Scrape finished with status={result.status} and no markdown payload."
            )


if __name__ == "__main__":
    main()
