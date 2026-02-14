from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


def test_profile_request_utils_use_profile_route_builder():
    module_text = Path(
        "hyperbrowser/client/managers/profile_request_utils.py"
    ).read_text(encoding="utf-8")
    assert "profile_route_constants import build_profile_route" in module_text
    assert "build_profile_route(profile_id)" in module_text
    assert 'f"{route_prefix}/{profile_id}"' not in module_text
