from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


def test_web_request_utils_reuse_job_request_helpers():
    module_text = Path("hyperbrowser/client/managers/web_request_utils.py").read_text(
        encoding="utf-8"
    )
    assert "job_request_utils import" in module_text
    assert "start_job(" in module_text
    assert "get_job_status(" in module_text
    assert "get_job(" in module_text
    assert "start_job_async(" in module_text
    assert "get_job_status_async(" in module_text
    assert "get_job_async(" in module_text
    assert "client.transport." not in module_text
    assert "parse_response_model(" not in module_text
