from hyperbrowser import AsyncHyperbrowser, Hyperbrowser
from hyperbrowser.tools import WebsiteExtractTool


def invalid_sync_requests(client: Hyperbrowser) -> None:
    client.sessions.create({"made_up_option": True})  # M,P
    client.web.fetch({})  # M,P
    client.web.fetch({"url": 42})  # M,P
    client.web.fetch(
        {  # P
            "url": "https://example.com",
            "outputs": {"formats": [{"type": "xml"}]},  # M
        }
    )
    client.sandboxes.create({"image_name": "node", "cpu": "four"})  # M,P
    client.sandboxes.create_image_build(
        {  # P
            "image_name": "custom_node",
            "input_sha256": "abc123",
            "input_size_bytes": 123,
            "source_platform": "linux/arm64",  # M
        }
    )
    client.sandboxes.list_image_builds({"status": "cancelled"})  # M,P
    client.sandboxes.start_from_snapshot({"image_name": "node"})  # M,P
    WebsiteExtractTool.runnable(
        client,
        {"urls": ["https://example.com"], "unknown": True},  # M,P
    )


async def invalid_async_requests(client: AsyncHyperbrowser) -> None:
    await client.sessions.create(
        {"screen": {"width": "wide", "height": 720}}  # M,P
    )
    await client.agents.browser_use.start({"task": 123})  # M,P
    await client.agents.browser_use.start(
        {"task": "Browse", "output_model_schema": True}  # M,P
    )
