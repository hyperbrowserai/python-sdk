import asyncio

import hyperbrowser.client.managers.agent_stop_utils as agent_stop_utils


def test_stop_agent_task_delegates_to_put_job_action():
    captured = {}

    def _fake_put_job_action(**kwargs):
        captured.update(kwargs)
        return {"parsed": True}

    original_put_job_action = agent_stop_utils.put_job_action
    agent_stop_utils.put_job_action = _fake_put_job_action
    try:
        result = agent_stop_utils.stop_agent_task(
            client=object(),
            route_prefix="/task/cua",
            job_id="job-123",
            operation_name="cua task stop",
        )
    finally:
        agent_stop_utils.put_job_action = original_put_job_action

    assert result == {"parsed": True}
    assert captured["route_prefix"] == "/task/cua"
    assert captured["job_id"] == "job-123"
    assert captured["action_suffix"] == "/stop"
    assert captured["operation_name"] == "cua task stop"


def test_stop_agent_task_async_delegates_to_put_job_action_async():
    captured = {}

    async def _fake_put_job_action_async(**kwargs):
        captured.update(kwargs)
        return {"parsed": True}

    original_put_job_action_async = agent_stop_utils.put_job_action_async
    agent_stop_utils.put_job_action_async = _fake_put_job_action_async
    try:
        result = asyncio.run(
            agent_stop_utils.stop_agent_task_async(
                client=object(),
                route_prefix="/task/hyper-agent",
                job_id="job-999",
                operation_name="hyper agent task stop",
            )
        )
    finally:
        agent_stop_utils.put_job_action_async = original_put_job_action_async

    assert result == {"parsed": True}
    assert captured["route_prefix"] == "/task/hyper-agent"
    assert captured["job_id"] == "job-999"
    assert captured["action_suffix"] == "/stop"
    assert captured["operation_name"] == "hyper agent task stop"
