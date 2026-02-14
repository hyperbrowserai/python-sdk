from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


ALLOWED_PARSE_RESPONSE_MODEL_MODULES = {
    "hyperbrowser/client/managers/model_request_utils.py",
    "hyperbrowser/client/managers/response_utils.py",
    "hyperbrowser/client/managers/session_utils.py",
}


def test_parse_response_model_usage_is_centralized():
    violating_modules: list[str] = []
    for module_path in sorted(
        Path("hyperbrowser/client/managers").rglob("*.py")
    ):
        module_text = module_path.read_text(encoding="utf-8")
        if "parse_response_model(" not in module_text:
            continue
        normalized_path = module_path.as_posix()
        if normalized_path not in ALLOWED_PARSE_RESPONSE_MODEL_MODULES:
            violating_modules.append(normalized_path)

    assert violating_modules == []
