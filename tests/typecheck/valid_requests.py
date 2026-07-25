from typing import Any, Dict

from pydantic import BaseModel

from hyperbrowser import AsyncHyperbrowser, Hyperbrowser
from hyperbrowser.models import (
    CreateSessionParams as LegacyCreateSessionParams,
    FetchParams as LegacyFetchParams,
)
from hyperbrowser.tools import WebsiteExtractTool


class ProductResult(BaseModel):
    name: str
    price: float


class StructuralProductSchema:
    @classmethod
    def model_json_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {"title": {"type": "string"}},
        }


def valid_sync_requests(client: Hyperbrowser) -> None:
    client.sessions.create(
        {
            "use_stealth": True,
            "screen": {"width": 1440, "height": 900},
            "profile": {
                "id": "profile_123",
                "persist_changes": True,
            },
        }
    )
    client.web.fetch(
        {
            "url": "https://example.com/products",
            "outputs": {
                "formats": [
                    "markdown",
                    {
                        "type": "json",
                        "schema": ProductResult,
                    },
                ],
                "storage_state": {
                    "local_storage": {"theme": "dark"},
                    "session_storage": {"cart": "active"},
                },
            },
            "browser": {
                "screen": {"width": 1280, "height": 720},
                "location": {"country": "US", "state": "CA"},
            },
        }
    )
    client.extract.start(
        {
            "urls": ["https://example.com/products"],
            "schema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "price": {"type": "number"},
                },
                "required": ["name", "price"],
            },
            "session_options": {
                "use_proxy": True,
                "screen": {"width": 1280, "height": 720},
            },
        }
    )
    client.agents.browser_use.start(
        {
            "task": "Return the product title",
            "output_model_schema": StructuralProductSchema,
        }
    )
    client.agents.browser_use.start(
        {
            "task": "Open the product page",
            "initial_actions": [{"open_tab": {"url": "https://example.com/products"}}],
            "sensitive_data": {"account_password": "secret"},
            "output_model_schema": {
                "type": "object",
                "properties": {"title": {"type": "string"}},
            },
            "session_options": {"use_stealth": True},
        }
    )
    client.sandboxes.create(
        {
            "image_name": "node",
            "cpu": 2,
            "memory_mib": 2048,
            "exposed_ports": [{"port": 3000, "auth": True}],
            "mounts": {
                "/workspace": {
                    "id": "volume_123",
                    "type": "rw",
                    "shared": False,
                }
            },
        }
    )

    client.sessions.create(LegacyCreateSessionParams(use_stealth=True))
    client.web.fetch(LegacyFetchParams(url="https://example.com"))
    client.sessions.update_profile_params(
        "session_123",
        {"persist_changes": True},
    )
    client.sessions.update_profile_params("session_123", True)
    client.sessions.update_profile_params("session_123", persist_changes=True)
    WebsiteExtractTool.runnable(
        client,
        {
            "urls": ["https://example.com"],
            "schema": '{"type": "object"}',
        },
    )


async def valid_async_requests(client: AsyncHyperbrowser) -> None:
    await client.sessions.create(
        {
            "use_proxy": True,
            "proxy_country": "US",
            "screen": {"width": 1366, "height": 768},
        }
    )
    await client.web.fetch(
        {
            "url": "https://example.com",
            "outputs": {
                "formats": [
                    {
                        "type": "json",
                        "prompt": "Return the page title",
                        "schema": True,
                    }
                ]
            },
        }
    )
    await client.agents.browser_use.start(
        {
            "task": "Find the support address",
            "session_options": {
                "use_stealth": True,
                "screen": {"width": 1280, "height": 800},
            },
        }
    )
    await client.sandboxes.create(
        {
            "snapshot_name": "ready-to-run",
            "exposed_ports": [{"port": 8080}],
        }
    )

    await client.sessions.create(LegacyCreateSessionParams(use_proxy=True))
    await client.web.fetch(LegacyFetchParams(url="https://example.com"))
