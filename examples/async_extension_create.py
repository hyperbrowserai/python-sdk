"""
Asynchronous extension create example.

Run:
    export HYPERBROWSER_API_KEY="your_api_key"
    export HYPERBROWSER_EXTENSION_ZIP="/absolute/path/to/extension.zip"
    python3 examples/async_extension_create.py
"""

import asyncio
import os

from hyperbrowser import AsyncHyperbrowser
from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.models.extension import CreateExtensionParams


async def main() -> None:
    extension_zip_path = os.getenv("HYPERBROWSER_EXTENSION_ZIP")
    if extension_zip_path is None:
        raise HyperbrowserError("Set HYPERBROWSER_EXTENSION_ZIP before running")

    async with AsyncHyperbrowser() as client:
        extension = await client.extensions.create(
            CreateExtensionParams(
                name="my-extension",
                file_path=extension_zip_path,
            )
        )
        print(f"Created extension: {extension.id} ({extension.name})")


if __name__ == "__main__":
    asyncio.run(main())
