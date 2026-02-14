from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


def test_agent_task_read_helpers_use_shared_job_route_builders():
    module_text = Path(
        "hyperbrowser/client/managers/agent_task_read_utils.py"
    ).read_text(encoding="utf-8")
    assert "job_route_builders import build_job_route, build_job_status_route" in module_text
    assert "build_job_route(route_prefix, job_id)" in module_text
    assert "build_job_status_route(route_prefix, job_id)" in module_text
    assert 'f"{route_prefix}/{job_id}"' not in module_text
    assert 'f"{route_prefix}/{job_id}/status"' not in module_text


def test_agent_stop_helpers_use_shared_job_route_builders():
    module_text = Path("hyperbrowser/client/managers/agent_stop_utils.py").read_text(
        encoding="utf-8"
    )
    assert "job_route_builders import build_job_action_route" in module_text
    assert 'build_job_action_route(route_prefix, job_id, "/stop")' in module_text
    assert 'f"{route_prefix}/{job_id}/stop"' not in module_text
