import asyncio
from types import SimpleNamespace

import hyperbrowser.client.managers.agent_start_utils as agent_start_utils


def test_start_agent_task_builds_start_url_and_parses_response():
    captured = {}

    class _SyncTransport:
        def post(self, url, data):
            captured["url"] = url
            captured["data"] = data
            return SimpleNamespace(data={"id": "job-1"})

    class _Client:
        transport = _SyncTransport()

        @staticmethod
        def _build_url(path: str) -> str:
            return f"https://api.example.test{path}"

    def _fake_parse_response_model(data, **kwargs):
        captured["parse_data"] = data
        captured["parse_kwargs"] = kwargs
        return {"parsed": True}

    original_parse = agent_start_utils.parse_response_model
    agent_start_utils.parse_response_model = _fake_parse_response_model
    try:
        result = agent_start_utils.start_agent_task(
            client=_Client(),
            route_prefix="/task/cua",
            payload={"task": "open docs"},
            model=object,
            operation_name="cua start",
        )
    finally:
        agent_start_utils.parse_response_model = original_parse

    assert result == {"parsed": True}
    assert captured["url"] == "https://api.example.test/task/cua"
    assert captured["data"] == {"task": "open docs"}
    assert captured["parse_data"] == {"id": "job-1"}
    assert captured["parse_kwargs"]["operation_name"] == "cua start"


def test_start_agent_task_async_builds_start_url_and_parses_response():
    captured = {}

    class _AsyncTransport:
        async def post(self, url, data):
            captured["url"] = url
            captured["data"] = data
            return SimpleNamespace(data={"id": "job-2"})

    class _Client:
        transport = _AsyncTransport()

        @staticmethod
        def _build_url(path: str) -> str:
            return f"https://api.example.test{path}"

    def _fake_parse_response_model(data, **kwargs):
        captured["parse_data"] = data
        captured["parse_kwargs"] = kwargs
        return {"parsed": True}

    original_parse = agent_start_utils.parse_response_model
    agent_start_utils.parse_response_model = _fake_parse_response_model
    try:
        result = asyncio.run(
            agent_start_utils.start_agent_task_async(
                client=_Client(),
                route_prefix="/task/browser-use",
                payload={"task": "browse"},
                model=object,
                operation_name="browser-use start",
            )
        )
    finally:
        agent_start_utils.parse_response_model = original_parse

    assert result == {"parsed": True}
    assert captured["url"] == "https://api.example.test/task/browser-use"
    assert captured["data"] == {"task": "browse"}
    assert captured["parse_data"] == {"id": "job-2"}
    assert captured["parse_kwargs"]["operation_name"] == "browser-use start"
