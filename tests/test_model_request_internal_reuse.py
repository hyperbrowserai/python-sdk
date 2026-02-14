from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


MODULES_THAT_MUST_REUSE_SHARED_MODEL_REQUEST_HELPERS = (
    "hyperbrowser/client/managers/computer_action_request_utils.py",
    "hyperbrowser/client/managers/extension_request_utils.py",
    "hyperbrowser/client/managers/job_request_utils.py",
    "hyperbrowser/client/managers/profile_request_utils.py",
    "hyperbrowser/client/managers/team_request_utils.py",
)

MODULE_DISALLOWED_MARKERS = {
    "hyperbrowser/client/managers/computer_action_request_utils.py": (
        "client.transport.",
        "parse_response_model(",
    ),
    "hyperbrowser/client/managers/extension_request_utils.py": (
        "client.transport.",
        "parse_response_model(",
    ),
    "hyperbrowser/client/managers/job_request_utils.py": (
        "client.transport.",
        "parse_response_model(",
    ),
    "hyperbrowser/client/managers/profile_request_utils.py": (
        "client.transport.",
        "parse_response_model(",
    ),
    "hyperbrowser/client/managers/team_request_utils.py": (
        "client.transport.",
        "parse_response_model(",
    ),
}


def test_request_helpers_reuse_shared_model_request_helpers():
    violating_modules: list[str] = []
    for module_path in MODULES_THAT_MUST_REUSE_SHARED_MODEL_REQUEST_HELPERS:
        module_text = Path(module_path).read_text(encoding="utf-8")
        if "model_request_utils import" not in module_text:
            violating_modules.append(module_path)
            continue
        if any(
            marker in module_text
            for marker in MODULE_DISALLOWED_MARKERS[module_path]
        ):
            violating_modules.append(module_path)

    assert violating_modules == []
