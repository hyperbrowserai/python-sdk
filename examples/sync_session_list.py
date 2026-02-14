"""
Example: list sessions synchronously with the Hyperbrowser SDK.

Run:
    export HYPERBROWSER_API_KEY="your_api_key"
    python3 examples/sync_session_list.py
"""

from hyperbrowser import Hyperbrowser
from hyperbrowser.models import SessionListParams


def main() -> None:
    with Hyperbrowser() as client:
        response = client.sessions.list(
            SessionListParams(
                page=1,
                limit=5,
            )
        )

        print(f"Success: {response.success}")
        print(f"Returned sessions: {len(response.data)}")
        for session in response.data:
            print(f"- {session.id} ({session.status})")


if __name__ == "__main__":
    main()
