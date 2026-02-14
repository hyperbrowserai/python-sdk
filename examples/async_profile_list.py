"""
Asynchronous profile listing example.

Run:
    export HYPERBROWSER_API_KEY="your_api_key"
    python3 examples/async_profile_list.py
"""

import asyncio

from hyperbrowser import AsyncHyperbrowser
from hyperbrowser.models import ProfileListParams


async def main() -> None:
    async with AsyncHyperbrowser() as client:
        response = await client.profiles.list(
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
    asyncio.run(main())
