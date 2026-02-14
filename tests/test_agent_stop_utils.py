import asyncio
from types import SimpleNamespace

import hyperbrowser.client.managers.agent_stop_utils as agent_stop_utils


def test_stop_agent_task_builds_endpoint_and_parses_response():
    captured_path = {}

    class _SyncTransport:
        def put(self, url):
            captured_path["url"] = url
            return SimpleNamespace(data={"success": True})

    class _Client:
        transport = _SyncTransport()

        @staticmethod
        def _build_url(path: str) -> str:
            return f"https://api.example.test{path}"

    result = agent_stop_utils.stop_agent_task(
        client=_Client(),
        route_prefix="/task/cua",
        job_id="job-123",
        operation_name="cua task stop",
    )

    assert captured_path["url"] == "https://api.example.test/task/cua/job-123/stop"
    assert result.success is True


def test_stop_agent_task_async_builds_endpoint_and_parses_response():
    captured_path = {}

    class _AsyncTransport:
        async def put(self, url):
            captured_path["url"] = url
            return SimpleNamespace(data={"success": True})

    class _Client:
        transport = _AsyncTransport()

        @staticmethod
        def _build_url(path: str) -> str:
            return f"https://api.example.test{path}"

    result = asyncio.run(
        agent_stop_utils.stop_agent_task_async(
            client=_Client(),
            route_prefix="/task/hyper-agent",
            job_id="job-999",
            operation_name="hyper agent task stop",
        )
    )

    assert (
        captured_path["url"]
        == "https://api.example.test/task/hyper-agent/job-999/stop"
    )
    assert result.success is True
