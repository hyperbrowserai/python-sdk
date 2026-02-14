from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


def test_profile_request_utils_reuse_model_request_helpers():
    module_text = Path(
        "hyperbrowser/client/managers/profile_request_utils.py"
    ).read_text(encoding="utf-8")
    assert "model_request_utils import" in module_text
    assert "post_model_request(" in module_text
    assert "get_model_request(" in module_text
    assert "delete_model_request(" in module_text
    assert "post_model_request_async(" in module_text
    assert "get_model_request_async(" in module_text
    assert "delete_model_request_async(" in module_text
    assert "client.transport." not in module_text
    assert "parse_response_model(" not in module_text


def test_team_request_utils_reuse_model_request_helpers():
    module_text = Path("hyperbrowser/client/managers/team_request_utils.py").read_text(
        encoding="utf-8"
    )
    assert "model_request_utils import get_model_request, get_model_request_async" in module_text
    assert "get_model_request(" in module_text
    assert "get_model_request_async(" in module_text
    assert "client.transport." not in module_text
    assert "parse_response_model(" not in module_text
