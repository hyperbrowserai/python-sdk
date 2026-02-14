"""
Asynchronous extension list example.

Run:
    export HYPERBROWSER_API_KEY="your_api_key"
    python3 examples/async_extension_list.py
"""

import asyncio

from hyperbrowser import AsyncHyperbrowser


async def main() -> None:
    async with AsyncHyperbrowser() as client:
        extensions = await client.extensions.list()
        for extension in extensions:
            print(f"{extension.id}: {extension.name}")


if __name__ == "__main__":
    asyncio.run(main())
