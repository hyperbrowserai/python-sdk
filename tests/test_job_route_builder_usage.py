from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


def test_job_request_helpers_use_route_builders():
    module_text = Path("hyperbrowser/client/managers/job_request_utils.py").read_text(
        encoding="utf-8"
    )
    assert (
        "job_route_builders import build_job_route, build_job_status_route"
        in module_text
    )
    assert "build_job_route(route_prefix, job_id)" in module_text
    assert "build_job_status_route(route_prefix, job_id)" in module_text
    assert 'f"{route_prefix}/{job_id}"' not in module_text
    assert 'f"{route_prefix}/{job_id}/status"' not in module_text


def test_web_request_helpers_reuse_job_request_helpers():
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
