import asyncio
from types import SimpleNamespace

import hyperbrowser.client.managers.agent_task_read_utils as agent_task_read_utils


def test_get_agent_task_builds_task_url_and_parses_payload():
    captured = {}

    class _SyncTransport:
        def get(self, url):
            captured["url"] = url
            return SimpleNamespace(data={"data": "ok"})

    class _Client:
        transport = _SyncTransport()

        @staticmethod
        def _build_url(path: str) -> str:
            return f"https://api.example.test{path}"

    def _fake_parse_response_model(data, **kwargs):
        captured["data"] = data
        captured["kwargs"] = kwargs
        return {"parsed": True}

    original_parse = agent_task_read_utils.parse_response_model
    agent_task_read_utils.parse_response_model = _fake_parse_response_model
    try:
        result = agent_task_read_utils.get_agent_task(
            client=_Client(),
            route_prefix="/task/cua",
            job_id="job-1",
            model=object,
            operation_name="cua task",
        )
    finally:
        agent_task_read_utils.parse_response_model = original_parse

    assert result == {"parsed": True}
    assert captured["url"] == "https://api.example.test/task/cua/job-1"
    assert captured["data"] == {"data": "ok"}
    assert captured["kwargs"]["operation_name"] == "cua task"


def test_get_agent_task_status_builds_status_url_and_parses_payload():
    captured = {}

    class _SyncTransport:
        def get(self, url):
            captured["url"] = url
            return SimpleNamespace(data={"status": "running"})

    class _Client:
        transport = _SyncTransport()

        @staticmethod
        def _build_url(path: str) -> str:
            return f"https://api.example.test{path}"

    def _fake_parse_response_model(data, **kwargs):
        captured["data"] = data
        captured["kwargs"] = kwargs
        return {"parsed": True}

    original_parse = agent_task_read_utils.parse_response_model
    agent_task_read_utils.parse_response_model = _fake_parse_response_model
    try:
        result = agent_task_read_utils.get_agent_task_status(
            client=_Client(),
            route_prefix="/task/hyper-agent",
            job_id="job-2",
            model=object,
            operation_name="hyper agent task status",
        )
    finally:
        agent_task_read_utils.parse_response_model = original_parse

    assert result == {"parsed": True}
    assert captured["url"] == "https://api.example.test/task/hyper-agent/job-2/status"
    assert captured["data"] == {"status": "running"}
    assert captured["kwargs"]["operation_name"] == "hyper agent task status"


def test_get_agent_task_async_builds_task_url_and_parses_payload():
    captured = {}

    class _AsyncTransport:
        async def get(self, url):
            captured["url"] = url
            return SimpleNamespace(data={"data": "ok"})

    class _Client:
        transport = _AsyncTransport()

        @staticmethod
        def _build_url(path: str) -> str:
            return f"https://api.example.test{path}"

    def _fake_parse_response_model(data, **kwargs):
        captured["data"] = data
        captured["kwargs"] = kwargs
        return {"parsed": True}

    original_parse = agent_task_read_utils.parse_response_model
    agent_task_read_utils.parse_response_model = _fake_parse_response_model
    try:
        result = asyncio.run(
            agent_task_read_utils.get_agent_task_async(
                client=_Client(),
                route_prefix="/task/claude-computer-use",
                job_id="job-3",
                model=object,
                operation_name="claude computer use task",
            )
        )
    finally:
        agent_task_read_utils.parse_response_model = original_parse

    assert result == {"parsed": True}
    assert (
        captured["url"] == "https://api.example.test/task/claude-computer-use/job-3"
    )
    assert captured["data"] == {"data": "ok"}
    assert captured["kwargs"]["operation_name"] == "claude computer use task"


def test_get_agent_task_status_async_builds_status_url_and_parses_payload():
    captured = {}

    class _AsyncTransport:
        async def get(self, url):
            captured["url"] = url
            return SimpleNamespace(data={"status": "running"})

    class _Client:
        transport = _AsyncTransport()

        @staticmethod
        def _build_url(path: str) -> str:
            return f"https://api.example.test{path}"

    def _fake_parse_response_model(data, **kwargs):
        captured["data"] = data
        captured["kwargs"] = kwargs
        return {"parsed": True}

    original_parse = agent_task_read_utils.parse_response_model
    agent_task_read_utils.parse_response_model = _fake_parse_response_model
    try:
        result = asyncio.run(
            agent_task_read_utils.get_agent_task_status_async(
                client=_Client(),
                route_prefix="/task/gemini-computer-use",
                job_id="job-4",
                model=object,
                operation_name="gemini computer use task status",
            )
        )
    finally:
        agent_task_read_utils.parse_response_model = original_parse

    assert result == {"parsed": True}
    assert (
        captured["url"]
        == "https://api.example.test/task/gemini-computer-use/job-4/status"
    )
    assert captured["data"] == {"status": "running"}
    assert captured["kwargs"]["operation_name"] == "gemini computer use task status"
