import asyncio

import hyperbrowser.client.managers.agent_start_utils as agent_start_utils


def test_start_agent_task_delegates_to_start_job():
    captured = {}

    def _fake_start_job(**kwargs):
        captured.update(kwargs)
        return {"parsed": True}

    original_start_job = agent_start_utils.start_job
    agent_start_utils.start_job = _fake_start_job
    try:
        result = agent_start_utils.start_agent_task(
            client=object(),
            route_prefix="/task/cua",
            payload={"task": "open docs"},
            model=object,
            operation_name="cua start",
        )
    finally:
        agent_start_utils.start_job = original_start_job

    assert result == {"parsed": True}
    assert captured["route_prefix"] == "/task/cua"
    assert captured["payload"] == {"task": "open docs"}
    assert captured["operation_name"] == "cua start"


def test_start_agent_task_async_delegates_to_start_job_async():
    captured = {}

    async def _fake_start_job_async(**kwargs):
        captured.update(kwargs)
        return {"parsed": True}

    original_start_job_async = agent_start_utils.start_job_async
    agent_start_utils.start_job_async = _fake_start_job_async
    try:
        result = asyncio.run(
            agent_start_utils.start_agent_task_async(
                client=object(),
                route_prefix="/task/browser-use",
                payload={"task": "browse"},
                model=object,
                operation_name="browser-use start",
            )
        )
    finally:
        agent_start_utils.start_job_async = original_start_job_async

    assert result == {"parsed": True}
    assert captured["route_prefix"] == "/task/browser-use"
    assert captured["payload"] == {"task": "browse"}
    assert captured["operation_name"] == "browser-use start"
