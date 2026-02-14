"""
Synchronous extension list example.

Run:
    export HYPERBROWSER_API_KEY="your_api_key"
    python3 examples/sync_extension_list.py
"""

from hyperbrowser import Hyperbrowser


def main() -> None:
    with Hyperbrowser() as client:
        extensions = client.extensions.list()
        for extension in extensions:
            print(f"{extension.id}: {extension.name}")


if __name__ == "__main__":
    main()
