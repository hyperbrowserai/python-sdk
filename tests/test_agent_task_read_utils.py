import asyncio

import hyperbrowser.client.managers.agent_task_read_utils as agent_task_read_utils


def test_get_agent_task_delegates_to_get_job():
    captured = {}

    def _fake_get_job(**kwargs):
        captured.update(kwargs)
        return {"parsed": True}

    original_get_job = agent_task_read_utils.get_job
    agent_task_read_utils.get_job = _fake_get_job
    try:
        result = agent_task_read_utils.get_agent_task(
            client=object(),
            route_prefix="/task/cua",
            job_id="job-1",
            model=object,
            operation_name="cua task",
        )
    finally:
        agent_task_read_utils.get_job = original_get_job

    assert result == {"parsed": True}
    assert captured["route_prefix"] == "/task/cua"
    assert captured["job_id"] == "job-1"
    assert captured["params"] is None
    assert captured["operation_name"] == "cua task"


def test_get_agent_task_status_delegates_to_get_job_status():
    captured = {}

    def _fake_get_job_status(**kwargs):
        captured.update(kwargs)
        return {"parsed": True}

    original_get_job_status = agent_task_read_utils.get_job_status
    agent_task_read_utils.get_job_status = _fake_get_job_status
    try:
        result = agent_task_read_utils.get_agent_task_status(
            client=object(),
            route_prefix="/task/hyper-agent",
            job_id="job-2",
            model=object,
            operation_name="hyper agent task status",
        )
    finally:
        agent_task_read_utils.get_job_status = original_get_job_status

    assert result == {"parsed": True}
    assert captured["route_prefix"] == "/task/hyper-agent"
    assert captured["job_id"] == "job-2"
    assert captured["operation_name"] == "hyper agent task status"


def test_get_agent_task_async_delegates_to_get_job_async():
    captured = {}

    async def _fake_get_job_async(**kwargs):
        captured.update(kwargs)
        return {"parsed": True}

    original_get_job_async = agent_task_read_utils.get_job_async
    agent_task_read_utils.get_job_async = _fake_get_job_async
    try:
        result = asyncio.run(
            agent_task_read_utils.get_agent_task_async(
                client=object(),
                route_prefix="/task/claude-computer-use",
                job_id="job-3",
                model=object,
                operation_name="claude computer use task",
            )
        )
    finally:
        agent_task_read_utils.get_job_async = original_get_job_async

    assert result == {"parsed": True}
    assert captured["route_prefix"] == "/task/claude-computer-use"
    assert captured["job_id"] == "job-3"
    assert captured["params"] is None
    assert captured["operation_name"] == "claude computer use task"


def test_get_agent_task_status_async_delegates_to_get_job_status_async():
    captured = {}

    async def _fake_get_job_status_async(**kwargs):
        captured.update(kwargs)
        return {"parsed": True}

    original_get_job_status_async = agent_task_read_utils.get_job_status_async
    agent_task_read_utils.get_job_status_async = _fake_get_job_status_async
    try:
        result = asyncio.run(
            agent_task_read_utils.get_agent_task_status_async(
                client=object(),
                route_prefix="/task/gemini-computer-use",
                job_id="job-4",
                model=object,
                operation_name="gemini computer use task status",
            )
        )
    finally:
        agent_task_read_utils.get_job_status_async = original_get_job_status_async

    assert result == {"parsed": True}
    assert captured["route_prefix"] == "/task/gemini-computer-use"
    assert captured["job_id"] == "job-4"
    assert captured["operation_name"] == "gemini computer use task status"
