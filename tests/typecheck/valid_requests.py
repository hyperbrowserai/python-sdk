from typing import Any, Dict

from pydantic import BaseModel

from hyperbrowser import AsyncHyperbrowser, Hyperbrowser
from hyperbrowser.models import (
    CreateSandboxImageBuildParams as LegacyCreateSandboxImageBuildParams,
    CreateSessionParams as LegacyCreateSessionParams,
    FetchParams as LegacyFetchParams,
    SandboxImageBuildListParams as LegacySandboxImageBuildListParams,
    VolumeListParams as LegacyVolumeListParams,
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
            "region": "us",
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
    client.agents.cua.start(
        {
            "task": "Complete the task",
            "use_custom_api_keys": True,
            "api_keys": {"openai": "openai-key"},
            "base_urls": {
                "openai": "https://example.openai.azure.com/openai/v1/",
            },
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
    client.sandboxes.create_image_build(
        {
            "image_name": "custom_node",
            "input_sha256": "abc123",
            "input_size_bytes": 123,
            "source_platform": "linux/amd64",
        }
    )
    client.sandboxes.create_image_build(
        {
            "image_name": "remote_context",
            "input_sha256": "a" * 64,
            "input_size_bytes": 123,
            "input_format": "dockerfile_context_manifest_v1",
            "source_platform": "linux/amd64",
            "dockerfile_path": "Dockerfile",
            "context_manifest": {
                "dockerfile_path": "Dockerfile",
                "context_mode": "sparse",
                "bundles": [
                    {
                        "sha256": "b" * 64,
                        "size_bytes": 10,
                        "uncompressed_size_bytes": 20,
                        "entry_count": 2,
                    }
                ],
            },
        }
    )
    client.sandboxes.reuse_docker_image(
        {
            "image_name": "custom_node",
            "source_image_digest": "sha256:" + "c" * 64,
            "source_platform": "linux/amd64",
            "image_init": {"working_dir": "/app"},
        }
    )
    client.sandboxes.create_image_build(
        LegacyCreateSandboxImageBuildParams(
            image_name="custom_node",
            input_sha256="abc123",
            input_size_bytes=123,
            source_platform="linux/amd64",
        )
    )
    client.sandboxes.list_image_builds({"status": "dispatching", "limit": -1})
    client.sandboxes.list_image_builds(
        LegacySandboxImageBuildListParams(status="verifying", limit=-1)
    )
    client.volumes.list({"page": 0, "limit": -1})
    client.volumes.list(LegacyVolumeListParams(page=0, limit=-1))
    client.volumes.delete("2d6f01cf-c5d7-4c61-ae9e-0264f1c8063d")

    client.sessions.create(LegacyCreateSessionParams(use_stealth=True, region="us"))
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
    await client.agents.cua.start(
        {
            "task": "Complete the task",
            "use_custom_api_keys": True,
            "api_keys": {"openai": "openai-key"},
            "base_urls": {
                "openai": "https://example.openai.azure.com/openai/v1/",
            },
        }
    )
    await client.sandboxes.create(
        {
            "snapshot_name": "ready-to-run",
            "exposed_ports": [{"port": 8080}],
        }
    )
    await client.sandboxes.create_image_build(
        {
            "image_name": "custom_node",
            "input_sha256": "abc123",
            "input_size_bytes": 123,
            "source_platform": "linux/amd64",
        }
    )
    await client.sandboxes.reuse_docker_image(
        {
            "image_name": "custom_node",
            "source_image_digest": "sha256:" + "c" * 64,
            "source_platform": "linux/amd64",
        }
    )
    await client.sandboxes.list_image_builds({"status": "verifying", "limit": -1})
    await client.volumes.list({"page": 0, "limit": -1})
    await client.volumes.delete("2d6f01cf-c5d7-4c61-ae9e-0264f1c8063d")

    await client.sessions.create(LegacyCreateSessionParams(use_proxy=True, region="us"))
    await client.web.fetch(LegacyFetchParams(url="https://example.com"))
