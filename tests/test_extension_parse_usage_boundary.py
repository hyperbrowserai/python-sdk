from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


ALLOWED_PARSE_EXTENSION_LIST_RESPONSE_DATA_MODULES = {
    "hyperbrowser/client/managers/extension_request_utils.py",
    "hyperbrowser/client/managers/extension_utils.py",
}


def test_parse_extension_list_response_data_usage_is_centralized():
    violating_modules: list[str] = []
    for module_path in sorted(
        Path("hyperbrowser/client/managers").rglob("*.py")
    ):
        module_text = module_path.read_text(encoding="utf-8")
        if "parse_extension_list_response_data(" not in module_text:
            continue
        normalized_path = module_path.as_posix()
        if normalized_path not in ALLOWED_PARSE_EXTENSION_LIST_RESPONSE_DATA_MODULES:
            violating_modules.append(normalized_path)

    assert violating_modules == []
