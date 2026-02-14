"""
Synchronous profile listing example.

Run:
    export HYPERBROWSER_API_KEY="your_api_key"
    python3 examples/sync_profile_list.py
"""

from hyperbrowser import Hyperbrowser
from hyperbrowser.models import ProfileListParams


def main() -> None:
    with Hyperbrowser() as client:
        response = client.profiles.list(
            ProfileListParams(
                page=1,
                limit=5,
            )
        )

        print(f"Profiles returned: {len(response.profiles)}")
        print(f"Page {response.page} of {response.total_pages}")
        for profile in response.profiles:
            print(f"- {profile.id} ({profile.name})")


if __name__ == "__main__":
    main()
