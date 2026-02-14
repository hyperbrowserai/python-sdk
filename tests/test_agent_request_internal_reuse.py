from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


def test_agent_start_helpers_reuse_job_request_helpers():
    module_text = Path("hyperbrowser/client/managers/agent_start_utils.py").read_text(
        encoding="utf-8"
    )
    assert "job_request_utils import start_job, start_job_async" in module_text
    assert "start_job(" in module_text
    assert "start_job_async(" in module_text
    assert "client.transport.post(" not in module_text
    assert "parse_response_model(" not in module_text


def test_agent_task_read_helpers_reuse_job_request_helpers():
    module_text = Path(
        "hyperbrowser/client/managers/agent_task_read_utils.py"
    ).read_text(encoding="utf-8")
    assert "job_request_utils import" in module_text
    assert "get_job(" in module_text
    assert "get_job_status(" in module_text
    assert "get_job_async(" in module_text
    assert "get_job_status_async(" in module_text
    assert "client.transport.get(" not in module_text
    assert "parse_response_model(" not in module_text


def test_agent_stop_helpers_reuse_job_request_helpers():
    module_text = Path("hyperbrowser/client/managers/agent_stop_utils.py").read_text(
        encoding="utf-8"
    )
    assert "job_request_utils import put_job_action, put_job_action_async" in module_text
    assert "put_job_action(" in module_text
    assert "put_job_action_async(" in module_text
    assert "client.transport.put(" not in module_text
    assert "parse_response_model(" not in module_text
