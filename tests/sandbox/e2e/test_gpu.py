"""Opt-in GPU smoke test. Requires a GPU-published CUDA image and a paid GPU-enabled team."""

import asyncio
import inspect
import os

import pytest

from hyperbrowser import AsyncHyperbrowser, Hyperbrowser

pytestmark = pytest.mark.skipif(
    not (
        os.getenv("HYPERBROWSER_API_KEY") and os.getenv("HYPERBROWSER_GPU_IMAGE_NAME")
    ),
    reason="Set HYPERBROWSER_API_KEY and HYPERBROWSER_GPU_IMAGE_NAME to run live GPU tests",
)


@pytest.mark.parametrize("asynchronous", [False, True], ids=["sync", "async"])
def test_gpu_lifecycle(asynchronous):
    async def call(value):
        return await value if inspect.isawaitable(value) else value

    async def run():
        client = (AsyncHyperbrowser if asynchronous else Hyperbrowser)(
            api_key=os.environ["HYPERBROWSER_API_KEY"],
            **(
                {"base_url": os.environ["HYPERBROWSER_BASE_URL"]}
                if os.getenv("HYPERBROWSER_BASE_URL")
                else {}
            ),
        )
        sandbox = None
        count = int(os.getenv("HYPERBROWSER_GPU_COUNT", "1"))
        try:
            sandbox = await call(
                client.sandboxes.create(
                    {
                        "image_name": os.environ["HYPERBROWSER_GPU_IMAGE_NAME"],
                        "gpu": os.getenv("HYPERBROWSER_GPU_TYPE", "L4"),
                        "gpu_count": count,
                        "preempt": os.getenv("HYPERBROWSER_GPU_PREEMPT", "true").lower()
                        != "false",
                        "region": "us",
                        "disk_mib": 65536,
                        "timeout_minutes": 30,
                    }
                )
            )
            await call(sandbox.wait_until_ready(timeout=20 * 60))
            devices = await call(
                sandbox.exec("nvidia-smi --query-gpu=uuid --format=csv,noheader")
            )
            assert devices.exit_code == 0
            assert len(devices.stdout.strip().splitlines()) == count
            await call(sandbox.files.write_text("/tmp/hb-gpu-sdk.txt", "gpu-sdk-ok"))
            assert (
                await call(sandbox.files.read_text("/tmp/hb-gpu-sdk.txt"))
                == "gpu-sdk-ok"
            )
            port = await call(sandbox.expose({"port": 8000, "auth": True}))
            assert port.auth and port.url
            await call(sandbox.unexpose(8000))
            await call(
                sandbox.update_network({"allow_out": ["example.com"], "deny_out": []})
            )
            await call(sandbox.clear_network())
            if os.getenv("HYPERBROWSER_GPU_DESKTOP") == "1":
                result = await call(sandbox.computer_action({"action": "screenshot"}))
                assert result.success and result.screenshot
        finally:
            try:
                if sandbox is not None:
                    await call(sandbox.stop())
            finally:
                await call(client.close())

    asyncio.run(run())
