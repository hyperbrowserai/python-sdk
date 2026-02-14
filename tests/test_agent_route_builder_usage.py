from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


def test_agent_task_read_helpers_reuse_job_request_helpers():
    module_text = Path(
        "hyperbrowser/client/managers/agent_task_read_utils.py"
    ).read_text(encoding="utf-8")
    assert "job_request_utils import" in module_text
    assert "get_job(" in module_text
    assert "get_job_status(" in module_text
    assert "get_job_async(" in module_text
    assert "get_job_status_async(" in module_text


def test_agent_stop_helpers_reuse_job_request_helpers():
    module_text = Path("hyperbrowser/client/managers/agent_stop_utils.py").read_text(
        encoding="utf-8"
    )
    assert "job_request_utils import put_job_action, put_job_action_async" in module_text
    assert "put_job_action(" in module_text
    assert "put_job_action_async(" in module_text
