from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


REQUEST_HELPER_MODULES = (
    "hyperbrowser/client/managers/agent_start_utils.py",
    "hyperbrowser/client/managers/agent_stop_utils.py",
    "hyperbrowser/client/managers/agent_task_read_utils.py",
    "hyperbrowser/client/managers/computer_action_request_utils.py",
    "hyperbrowser/client/managers/extension_request_utils.py",
    "hyperbrowser/client/managers/job_request_utils.py",
    "hyperbrowser/client/managers/profile_request_utils.py",
    "hyperbrowser/client/managers/session_request_utils.py",
    "hyperbrowser/client/managers/team_request_utils.py",
    "hyperbrowser/client/managers/web_request_utils.py",
)


def test_request_helpers_do_not_import_response_utils_directly():
    violating_modules: list[str] = []
    for module_path in REQUEST_HELPER_MODULES:
        module_text = Path(module_path).read_text(encoding="utf-8")
        if "response_utils import" in module_text:
            violating_modules.append(module_path)

    assert violating_modules == []
