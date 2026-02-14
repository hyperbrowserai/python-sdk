from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


def test_extension_request_utils_reuse_model_request_helpers():
    module_text = Path(
        "hyperbrowser/client/managers/extension_request_utils.py"
    ).read_text(encoding="utf-8")
    assert "model_request_utils import post_model_request, post_model_request_async" in module_text
    assert "post_model_request(" in module_text
    assert "post_model_request_async(" in module_text
    assert "client.transport.post(" not in module_text
    assert "parse_response_model(" not in module_text
