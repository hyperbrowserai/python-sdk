from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from hyperbrowser import AsyncHyperbrowser, Hyperbrowser
from hyperbrowser.build_context import docker_build_context_fingerprint
from hyperbrowser.models import (
    CreateSandboxImageBuildParams as LegacyCreateSandboxImageBuildParams,
    CreateSessionParams as LegacyCreateSessionParams,
    FetchParams as LegacyFetchParams,
    SandboxImageBuildListParams as LegacySandboxImageBuildListParams,
    VolumeListParams as LegacyVolumeListParams,
    CreateSecretParams as LegacyCreateSecretParams,
    CreateVaultParams as LegacyCreateVaultParams,
    SecretReference as LegacySecretReference,
    ScrollActionParams as LegacyScrollActionParams,
    ScrollAtCursorActionParams as LegacyScrollAtCursorActionParams,
    ComputerActionResponseData,
    ComputerActionResponseDataListWindows,
    ComputerActionResponseDataCursorPosition,
    ComputerActionResponse,
)
from hyperbrowser.types import ScrollActionParams
from hyperbrowser.tools import CredentialFillTool, WebsiteExtractTool


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
            "llm": "gpt-6.1-terra",
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
    client.agents.gemini_computer_use.start(
        {
            "task": "Complete the task",
            "llm": "gemini-4-argon",
            "reasoning_effort": "high",
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
            "llm": "muse-wonder-1.0",
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
    client.secrets.list({"search": "provider", "limit": 100})
    client.secrets.create({"name": "provider-key", "value": b"value"})
    client.secrets.create(LegacyCreateSecretParams(name="provider-key", value="v"))
    client.secrets.update("provider-key", {"description": "rotated"})
    client.secrets.add_version("provider-key", "next value")
    client.secrets.delete_version("provider-key", 1)
    client.sandboxes.create(
        {
            "image_name": "node",
            "secrets": {
                "API_KEY": "provider-key",
                "OTHER": {"name": "o", "version": 2},
            },
        }
    )
    sandbox = client.sandboxes.get("sandbox_123")
    sandbox.exec(
        "node app.js",
        secrets={
            "API_KEY": {"name": "provider-key", "version": "latest"},
            "OTHER": LegacySecretReference(name="o", version=2),
        },
    )

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
    await client.agents.gemini_computer_use.start(
        {
            "task": "Complete the task",
            "llm": "gemini-3.6-flash",
            "reasoning_effort": "minimal",
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
            "llm": "muse-wonder-1.0",
            "reasoning_effort": "max",
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
    await client.secrets.create({"name": "provider-key", "description": "d"})
    await client.secrets.get("provider-key")
    async_sandbox = await client.sandboxes.get("sandbox_123")
    await async_sandbox.processes.start("node app.js", secrets={"API_KEY": "k"})

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
    from hyperbrowser.models import (
        WebMCPInvokeParams,
        WebMCPStartParams,
        WebMCPResultParams,
    )

    client.sessions.create({"enable_web_mcp": True})
    tools = client.sessions.webmcp.list_tools("session")
    tool = tools.tools[0]
    client.sessions.webmcp.invoke(
        "session", {"tool_ref": tool.tool_ref, "input": {"customKey": 1}}
    )
    client.sessions.webmcp.invoke("session", WebMCPInvokeParams(tool_ref=tool.tool_ref))
    handle = client.sessions.webmcp.start(
        "session", WebMCPStartParams(tool_ref=tool.tool_ref, timeout_seconds=600)
    )
    client.sessions.webmcp.get_result(
        "session", handle.invocation_id, WebMCPResultParams(wait_seconds=30)
    )
    client.sessions.webmcp.cancel("session", handle.invocation_id)


async def valid_async_webmcp_requests(client: AsyncHyperbrowser) -> None:
    await client.sessions.create({"enable_web_mcp": True})
    tools = await client.sessions.webmcp.list_tools("session")
    await client.sessions.webmcp.invoke(
        "session", {"tool_ref": tools.tools[0].tool_ref}
    )
    handle = await client.sessions.webmcp.start(
        "session", {"tool_ref": tools.tools[0].tool_ref, "timeout_seconds": 600}
    )
    await client.sessions.webmcp.get_result(
        "session", handle.invocation_id, {"wait_seconds": 30}
    )
    await client.sessions.webmcp.cancel("session", handle.invocation_id)


def valid_web_bot_auth_and_proxy_routes_requests(client: Hyperbrowser) -> None:
    from hyperbrowser.models import ProxyRoute, WebBotAuthParams

    client.sessions.create({"web_bot_auth": True})
    client.sessions.create({"web_bot_auth": {"only_domains": ["example.com"]}})
    client.sessions.create(
        {
            "use_proxy": True,
            "proxy_routes": [
                {"match": "api.example.com", "proxy": "default"},
                {"match": ["*.example.com", "cdn.example.net"], "proxy": "direct"},
            ],
        }
    )
    client.sessions.create(
        LegacyCreateSessionParams(
            web_bot_auth=WebBotAuthParams(only_domains=["example.com"]),
            use_proxy=True,
            proxy_routes=[ProxyRoute(match="*", proxy="direct")],
        )
    )
    client.agents.browser_use.start(
        {"task": "Open example.com", "session_options": {"web_bot_auth": True}}
    )


async def valid_async_web_bot_auth_and_proxy_routes_requests(
    client: AsyncHyperbrowser,
) -> None:
    await client.sessions.create({"web_bot_auth": {"only_domains": ["example.com"]}})
    await client.sessions.create(
        {"use_proxy": True, "proxy_routes": [{"match": "*", "proxy": "direct"}]}
    )


def valid_credential_requests(client: Hyperbrowser) -> None:
    from hyperbrowser.models import (
        CredentialFillField,
        FillCredentialParams,
        OnePasswordField,
        OnePasswordFillSource,
        OnePasswordSource,
        SecretMetadata,
        SessionCredentialOnePassword,
        StoredEntry,
        UpdateSecretParams,
        UpdateVaultParams,
        VaultEntry,
    )

    secret = client.secrets.create(
        {
            "name": "github-password",
            "value": "pw",
            "allowed_origins": ["https://github.com"],
            "description": "GitHub password",
        }
    )
    kind: str = secret.type
    origins = secret.metadata.browser.allowed_origins if secret.metadata.browser else []
    client.secrets.create(
        {
            "name": "github-otp",
            "type": "totp",
            "metadata": {"browser": {"allowed_origins": origins}},
            "value": "JBSWY3DPEHPK3PXP",
        }
    )
    client.secrets.create({"name": "op-token", "type": "op_token", "value": "ops_x"})
    client.secrets.create(
        LegacyCreateSecretParams(name="github-otp", type="totp", value="JBSWY3DP")
    )
    client.secrets.add_version("github-otp", "otpauth://totp/x?secret=JBSWY3DP")
    client.secrets.set_allowed_origins("github-password", ["https://github.com"])
    client.secrets.set_allowed_origins("github-password", None)
    client.secrets.update("github-password", {"metadata": {"browser": None}})
    client.secrets.update(
        "github-password", UpdateSecretParams(metadata=SecretMetadata(browser=None))
    )
    client.secrets.list({"type": "totp"})

    vault = client.vaults.create(
        {
            "name": "github-login",
            "entries": {
                "USERNAME": {"name": "github-username"},
                "PASSWORD": {"name": "github-password", "version": 2},
                "OTP": {"name": "github-otp", "version": "latest"},
            },
        }
    )
    for env, entry in vault.entries.items():
        stored: VaultEntry = entry
        print(env, stored.name, stored.secret_id, stored.version)
    client.vaults.create(
        LegacyCreateVaultParams(
            name="github-otp",
            entries={"OTP": StoredEntry(name="github-otp", version="latest")},
        )
    )
    client.vaults.update("github-login", {"entries": {"OTP": None}})
    client.vaults.update(
        "github-login",
        UpdateVaultParams(entries={"OTP": StoredEntry(name="github-otp"), "X": None}),
    )
    listing = client.vaults.list({"search": "git", "limit": 10})
    print(listing.total_count, client.vaults.get("github-login").id)
    client.vaults.delete("github-login")

    sandbox = client.sandboxes.create(
        {
            "image_name": "node",
            "vault": "github-login",
            "secrets": {"A": "b"},
            "one_password": {
                "token": "op-token",
                "vault": "Engineering",
                "fields": {
                    "DB_PASS": {
                        "item": "Postgres",
                        "section": "prod",
                        "field": "password",
                    },
                    "DB_OTP": {"item": "Postgres", "field": "otp?attribute=totp"},
                },
            },
        }
    )
    print(sandbox.startup_secrets)
    handle = sandbox.processes.start("node app.js", vault="prod-db")
    for binding in handle.secrets or []:
        source_type = binding.source.type if binding.source else None
        print(binding.env, binding.name, binding.reference, binding.token_secret)
        print(source_type)
    sandbox.exec("node app.js", vault="prod-db", secrets={"A": "b"})
    sandbox.exec(
        "node app.js",
        one_password={
            "token": "op-token",
            "vault": "Engineering",
            "fields": {"DB_PASS": {"item": "Postgres", "field": "password"}},
        },
    )
    sandbox.processes.start(
        {
            "command": "node app.js",
            "one_password": {
                "token": "t",
                "vault": "v",
                "fields": {"A": {"item": "i", "field": "f"}},
            },
        }
    )
    sandbox.processes.start(
        "node app.js",
        one_password=OnePasswordSource(
            token="op-token",
            vault="Engineering",
            fields={"DB_PASS": OnePasswordField(item="Postgres", field="password")},
        ),
    )

    session = client.sessions.create(
        {"credentials": [kind, {"secret": "github-otp"}, {"vault": "github-login"}]}
    )
    for attached in session.credentials or []:
        print(attached.id, attached.name)
    client.sessions.create(LegacyCreateSessionParams(credentials=["github-password"]))
    result = client.sessions.credentials.fill(
        session.id,
        {
            "vault": "github-login",
            "fields": [
                {"field": "USERNAME", "selector": "#login"},
                {"field": "OTP", "selector": "#otp"},
            ],
            "page_url": "https://github.com/login",
            "frame_url": "https://github.com/",
        },
    )
    outcomes = [
        (field.selector, field.field, field.outcome, field.expires_at)
        for field in result.fields
    ]
    print(result.version, result.page_id, result.origin, outcomes)
    client.sessions.credentials.fill(
        session.id,
        FillCredentialParams(
            credential="github-password",
            fields=[CredentialFillField(selector="#pw")],
            page_id="PAGE",
        ),
    )
    client.sessions.create(
        {"credentials": [{"one_password": "op-token"}, {"secret": "github-otp"}]}
    )
    filled = client.sessions.credentials.fill(
        session.id,
        {
            "one_password": {
                "token": "op-token",
                "vault": "Engineering",
                "allowed_origins": ["https://github.com"],
            },
            "fields": [
                {"selector": "#login", "ref": {"item": "GitHub", "field": "username"}},
                {
                    "selector": "#otp",
                    "ref": {"item": "GitHub", "section": "2FA", "field": "otp"},
                },
            ],
            "page_url": "https://github.com/login",
        },
    )
    references: List[Optional[str]] = [field.reference for field in filled.fields]
    print(filled.version, references)
    client.sessions.credentials.fill(
        session.id,
        FillCredentialParams(
            one_password=OnePasswordFillSource(
                token="op-token",
                vault="Engineering",
                allowed_origins=["https://github.com"],
            ),
            fields=[
                CredentialFillField(
                    selector="#pw",
                    ref=OnePasswordField(item="GitHub", field="password"),
                )
            ],
        ),
    )
    client.sessions.create(
        LegacyCreateSessionParams(
            credentials=[SessionCredentialOnePassword(one_password="op-token")]
        )
    )
    text: str = CredentialFillTool.runnable(client, session.id, {"vault": "x"})
    print(text, CredentialFillTool.gemini_tool_definition["name"])


async def valid_async_credential_requests(client: AsyncHyperbrowser) -> None:
    await client.secrets.create(
        {"name": "github-otp", "type": "totp", "value": "JBSWY3DP"}
    )
    await client.secrets.set_allowed_origins("github-otp", None)
    await client.secrets.add_version("github-otp", "JBSWY3DP")
    vault = await client.vaults.create(
        {"name": "github-login", "entries": {"OTP": {"name": "github-otp"}}}
    )
    await client.vaults.update(vault.id, {"entries": {"OTP": None}})
    await client.vaults.delete(vault.name)
    session = await client.sessions.create({"credentials": [{"vault": "github-login"}]})
    result = await client.sessions.credentials.fill(
        session.id,
        {"vault": "github-login", "fields": [{"field": "OTP", "selector": "#otp"}]},
    )
    print(result.fields)
    await client.sessions.credentials.fill(
        session.id,
        {
            "one_password": {
                "token": "op-token",
                "vault": "v",
                "allowed_origins": ["https://*.example.com"],
            },
            "fields": [{"selector": "#otp", "ref": {"item": "i", "field": "otp"}}],
        },
    )
    sandbox = await client.sandboxes.create({"image_name": "node", "vault": "v"})
    await sandbox.processes.start("node app.js", vault="v")
    await sandbox.exec(
        "node app.js",
        one_password={
            "token": "t",
            "vault": "v",
            "fields": {"A": {"item": "i", "field": "f"}},
        },
    )
    text: str = await CredentialFillTool.async_runnable(
        client, session.id, {"credential": "x"}
    )
    print(text)


def valid_gpu_requests(client: Hyperbrowser) -> None:
    sandbox = client.sandboxes.create({
        "image_name": "cuda", "gpu": "H100", "gpu_count": 2,
        "preempt": False, "disk_mib": 524288,
    })
    sandbox.wait_until_ready(timeout=1200, poll_interval=3)
    sandbox.computer_action({"action": "screenshot"})
    client.sandboxes.get_or_build_image(context_path=".", enable_gpu_builds=True)
    client.sandboxes.create_image_build({
        "image_name": "cuda", "input_sha256": "a" * 64, "input_size_bytes": 1,
        "input_format": "dockerfile_context_manifest_v1", "enable_gpu_builds": True,
    })
    client.sandboxes.wait_for_image_build("build", enable_gpu_builds=True)


async def valid_async_gpu_requests(client: AsyncHyperbrowser) -> None:
    sandbox = await client.sandboxes.create({
        "image_name": "cuda", "gpu": "B300", "gpu_count": 8, "preempt": False,
    })
    await sandbox.wait_until_ready()
    await sandbox.computer_action({"action": "click", "x": 1, "y": 2})
    await client.sandboxes.build_image_from_dockerfile(
        context_path=".", image_name="cuda", enable_gpu_builds=True,
    )
