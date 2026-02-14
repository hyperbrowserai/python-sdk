from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


def test_session_request_utils_reuse_shared_model_request_raw_helpers():
    module_text = Path("hyperbrowser/client/managers/session_request_utils.py").read_text(
        encoding="utf-8"
    )
    assert "model_request_utils import (" in module_text
    assert "post_model_response_data(" in module_text
    assert "get_model_response_data(" in module_text
    assert "put_model_response_data(" in module_text
    assert "post_model_response_data_async(" in module_text
    assert "get_model_response_data_async(" in module_text
    assert "put_model_response_data_async(" in module_text
    assert "client.transport." not in module_text
