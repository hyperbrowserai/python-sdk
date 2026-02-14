from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


MODULES = (
    "hyperbrowser/client/managers/job_request_utils.py",
    "hyperbrowser/client/managers/web_request_utils.py",
)


def test_job_and_web_request_helpers_use_route_builders():
    for module_path in MODULES:
        module_text = Path(module_path).read_text(encoding="utf-8")
        assert "job_route_builders import build_job_route, build_job_status_route" in module_text
        assert "build_job_route(route_prefix, job_id)" in module_text
        assert "build_job_status_route(route_prefix, job_id)" in module_text
        assert 'f"{route_prefix}/{job_id}"' not in module_text
        assert 'f"{route_prefix}/{job_id}/status"' not in module_text
