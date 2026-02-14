"""
Synchronous team credit info example.

Run:
    export HYPERBROWSER_API_KEY="your_api_key"
    python3 examples/sync_team_credit_info.py
"""

from hyperbrowser import Hyperbrowser


def main() -> None:
    with Hyperbrowser() as client:
        credit_info = client.team.get_credit_info()
        print(f"Usage: {credit_info.usage}")
        print(f"Limit: {credit_info.limit}")
        print(f"Remaining: {credit_info.remaining}")


if __name__ == "__main__":
    main()
