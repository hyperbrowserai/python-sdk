from typing import Any, Dict

from pydantic import BaseModel

from hyperbrowser import AsyncHyperbrowser, Hyperbrowser
from hyperbrowser.build_context import docker_build_context_fingerprint
from hyperbrowser.models import (
    CreateSandboxImageBuildParams as LegacyCreateSandboxImageBuildParams,
    CreateSessionParams as LegacyCreateSessionParams,
    FetchParams as LegacyFetchParams,
    SandboxImageBuildListParams as LegacySandboxImageBuildListParams,
    VolumeListParams as LegacyVolumeListParams,
    ScrollActionParams as LegacyScrollActionParams,
    ScrollAtCursorActionParams as LegacyScrollAtCursorActionParams,
    ComputerActionResponseData,
    ComputerActionResponseDataListWindows,
    ComputerActionResponseDataCursorPosition,
    ComputerActionResponse,
)
from hyperbrowser.types import ScrollActionParams
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
            "llm": "gpt-6.1-sol",
            "reasoning_effort": "high",
            "use_custom_api_keys": True,
            "api_keys": {"openai": "openai-key"},
            "base_urls": {
                "openai": "https://example.openai.azure.com/openai/v1/",
            },
        }
    )
    client.agents.claude_computer_use.start(
        {
            "task": "Complete the task",
            "llm": "claude-opus-5-5",
            "reasoning_effort": "xhigh",
        }
    )
    client.agents.jev_computer_use.start(
        {
            "task": "Find the order",
            "llm": "jev-1.13.0",
            "text_llm": "gemini-3.5-flash-lite",
            "use_custom_api_keys": True,
            "api_keys": {"jev": "jev-key", "google": "google-key"},
        }
    )
    client.agents.meta_computer_use.start(
        {
            "task": "Complete the task",
            "llm": "muse-spark-1.3",
            "reasoning_effort": "max",
            "use_custom_api_keys": True,
            "api_keys": {"meta": "meta-key"},
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
            "builder_cpus": 8,
            "builder_memory_mib": 16384,
            "builder_scratch_mib": 65536,
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
            builder_cpus=8,
            builder_memory_mib=16384,
            builder_scratch_mib=65536,
        )
    )
    resolution = client.sandboxes.get_or_build_image(
        context_path=".",
        image_name_prefix="example",
        force_build=False,
        image_init={"env": {"MY_SETTING": "value"}},
        wait_timeout=600,
    )
    client.sandboxes.find_ready_image(resolution.image_name)
    client.sandboxes.build_image_from_dockerfile(
        context_path=".",
        image_name="custom",
        expected_context_fingerprint=docker_build_context_fingerprint("."),
        builder_cpus=8,
        builder_memory_mib=16384,
        builder_scratch_mib=65536,
    )
    client.sandboxes.build_image_from_docker_image(
        docker_image="local/app:latest",
        image_name="custom",
        builder_cpus=None,
        builder_memory_mib=16384,
        builder_scratch_mib=None,
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
            "llm": "gpt-6-luna",
            "reasoning_effort": "none",
            "use_custom_api_keys": True,
            "api_keys": {"openai": "openai-key"},
            "base_urls": {
                "openai": "https://example.openai.azure.com/openai/v1/",
            },
        }
    )
    await client.agents.claude_computer_use.start(
        {
            "task": "Complete the task",
            "llm": "claude-sonnet-5-5",
            "reasoning_effort": "max",
        }
    )
    await client.agents.jev_computer_use.start(
        {
            "task": "Find the order",
            "llm": "jev-latest",
            "text_llm": "gemini-3.5-flash-lite",
        }
    )
    await client.agents.meta_computer_use.start(
        {
            "task": "Complete the task",
            "llm": "muse-spark-1.2",
            "reasoning_effort": "xhigh",
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
            "builder_cpus": 8,
            "builder_memory_mib": 16384,
            "builder_scratch_mib": 65536,
        }
    )
    await client.sandboxes.create_image_build(
        LegacyCreateSandboxImageBuildParams(
            image_name="custom_node",
            input_sha256="abc123",
            input_size_bytes=123,
            builder_cpus=8,
            builder_memory_mib=16384,
            builder_scratch_mib=65536,
        )
    )
    resolution = await client.sandboxes.get_or_build_image(
        docker_image="local/app:latest",
        image_name_prefix="example",
        wait=False,
        expected_image_digest="sha256:" + "a" * 64,
    )
    await client.sandboxes.find_ready_image(resolution.image_name)
    await client.sandboxes.build_image_from_dockerfile(
        context_path=".",
        image_name="custom",
        expected_context_fingerprint="a" * 64,
        builder_cpus=8,
        builder_memory_mib=16384,
        builder_scratch_mib=65536,
    )
    await client.sandboxes.build_image_from_docker_image(
        docker_image="local/app:latest",
        image_name="custom",
        builder_cpus=None,
        builder_memory_mib=16384,
        builder_scratch_mib=None,
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


def valid_sync_computer_actions(client: Hyperbrowser) -> None:
    client.computer_action.cursor_position("session-id", return_screenshot=True)
    client.computer_action._execute_request("session-id", {"action": "cursor_position"})
    client.computer_action.click("session-id", 10, 20, keys=["Control_L"])
    client.computer_action.drag("session-id", [{"x": 1, "y": 2}], keys=["Shift_L"])
    client.computer_action.scroll("session-id", 10, 20, 0, 1, keys=["Alt_L"])
    client.computer_action.scroll_at_cursor("session-id", scroll_y=1, keys=["Alt_L"])
    client.computer_action._execute_request(
        "session-id", {"action": "scroll", "scroll_x": 0, "scroll_y": 1}
    )
    client.computer_action._execute_request(
        "session-id", LegacyScrollAtCursorActionParams(scroll_x=0, scroll_y=1)
    )
    cursor: ComputerActionResponse = client.computer_action.cursor_position(
        "session-id"
    )
    if isinstance(cursor.data, ComputerActionResponseDataCursorPosition):
        x: int = cursor.data.x
        y: int = cursor.data.y
        print(x, y)


def valid_sync_process_collection(client: Hyperbrowser) -> None:
    sandbox = client.sandboxes.get("sandbox-id")
    sandbox.exec("echo hello", max_output_bytes=1024)
    process = sandbox.processes.start({"command": "echo hello"}, max_output_bytes=1024)
    process.wait(timeout_sec=10)
    process.disconnect()


async def valid_async_computer_actions(client: AsyncHyperbrowser) -> None:
    await client.computer_action.cursor_position("session-id")
    await client.computer_action._execute_request(
        "session-id", {"action": "cursor_position"}
    )
    await client.computer_action.click("session-id", keys=["Control_L"])
    await client.computer_action.drag(
        "session-id", [{"x": 1, "y": 2}], keys=["Shift_L"]
    )
    await client.computer_action.scroll("session-id", 10, 20, 0, 1, keys=["Alt_L"])
    await client.computer_action.scroll_at_cursor(
        "session-id", scroll_y=1, keys=["Alt_L"]
    )
    await client.computer_action._execute_request(
        "session-id", {"action": "scroll", "scroll_x": 0, "scroll_y": 1}
    )
    await client.computer_action._execute_request(
        "session-id", LegacyScrollAtCursorActionParams(scroll_x=0, scroll_y=1)
    )
    cursor: ComputerActionResponse = await client.computer_action.cursor_position(
        "session-id"
    )
    if isinstance(cursor.data, ComputerActionResponseDataCursorPosition):
        x: int = cursor.data.x
        y: int = cursor.data.y
        print(x, y)


def existing_scroll_model_consumer(params: LegacyScrollActionParams) -> int:
    return params.x + params.y


def existing_scroll_dict_consumer(params: ScrollActionParams) -> int:
    return params["x"] + params["y"]


def shared_response_consumer(data: ComputerActionResponseData) -> str:
    if isinstance(data, ComputerActionResponseDataCursorPosition):
        return str(data.x)
    if isinstance(data, ComputerActionResponseDataListWindows):
        return data.active_window_id
    return data.clipboard_text or ""


async def valid_async_process_collection(client: AsyncHyperbrowser) -> None:
    sandbox = await client.sandboxes.get("sandbox-id")
    await sandbox.exec("echo hello", max_output_bytes=1024)
    process = await sandbox.processes.start(
        {"command": "echo hello"}, max_output_bytes=1024
    )
    await process.wait(timeout_sec=10)
    await process.disconnect()


def valid_webmcp_requests(client: Hyperbrowser) -> None:
    from hyperbrowser.models import WebMCPInvokeParams, WebMCPStartParams, WebMCPResultParams
    client.sessions.create({"enable_web_mcp": True})
    tools = client.sessions.webmcp.list_tools("session")
    tool = tools.tools[0]
    client.sessions.webmcp.invoke("session", {"tool_ref": tool.tool_ref, "input": {"customKey": 1}})
    client.sessions.webmcp.invoke("session", WebMCPInvokeParams(tool_ref=tool.tool_ref))
    handle = client.sessions.webmcp.start("session", WebMCPStartParams(tool_ref=tool.tool_ref, timeout_seconds=600))
    client.sessions.webmcp.get_result("session", handle.invocation_id, WebMCPResultParams(wait_seconds=30))
    client.sessions.webmcp.cancel("session", handle.invocation_id)


async def valid_async_webmcp_requests(client: AsyncHyperbrowser) -> None:
    await client.sessions.create({"enable_web_mcp": True})
    tools = await client.sessions.webmcp.list_tools("session")
    await client.sessions.webmcp.invoke("session", {"tool_ref": tools.tools[0].tool_ref})
    handle = await client.sessions.webmcp.start("session", {"tool_ref": tools.tools[0].tool_ref, "timeout_seconds": 600})
    await client.sessions.webmcp.get_result("session", handle.invocation_id, {"wait_seconds": 30})
    await client.sessions.webmcp.cancel("session", handle.invocation_id)
