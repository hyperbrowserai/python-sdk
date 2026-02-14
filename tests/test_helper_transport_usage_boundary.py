from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


ALLOWED_TRANSPORT_HELPER_MODULES = {
    "hyperbrowser/client/managers/model_request_utils.py",
}


def test_helper_modules_centralize_transport_usage_in_model_request_utils():
    violating_modules: list[str] = []
    for module_path in sorted(
        Path("hyperbrowser/client/managers").rglob("*.py")
    ):
        module_text = module_path.read_text(encoding="utf-8")
        if "client.transport." not in module_text:
            continue
        normalized_path = module_path.as_posix()
        if normalized_path not in ALLOWED_TRANSPORT_HELPER_MODULES:
            violating_modules.append(normalized_path)

    assert violating_modules == []
