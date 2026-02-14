"""
Example: synchronous web search with the Hyperbrowser SDK.

Run:
    export HYPERBROWSER_API_KEY="your_api_key"
    python3 examples/sync_web_search.py
"""

from hyperbrowser import Hyperbrowser
from hyperbrowser.models import WebSearchParams


def main() -> None:
    with Hyperbrowser() as client:
        response = client.web.search(
            WebSearchParams(
                query="Hyperbrowser Python SDK",
                page=1,
            )
        )

        print(f"Job ID: {response.job_id}")
        print(f"Status: {response.status}")

        if not response.data:
            print("No results returned.")
            return

        print(f"Query: {response.data.query}")
        for index, result in enumerate(response.data.results[:5], start=1):
            print(f"{index}. {result.title} -> {result.url}")


if __name__ == "__main__":
    main()
