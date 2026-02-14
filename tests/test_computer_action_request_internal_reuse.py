from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


def test_computer_action_request_utils_reuse_model_request_endpoint_helpers():
    module_text = Path(
        "hyperbrowser/client/managers/computer_action_request_utils.py"
    ).read_text(encoding="utf-8")
    assert "model_request_utils import" in module_text
    assert "post_model_request_to_endpoint(" in module_text
    assert "post_model_request_to_endpoint_async(" in module_text
    assert "client.transport.post(" not in module_text
    assert "parse_response_model(" not in module_text
