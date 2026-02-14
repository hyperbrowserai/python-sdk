from pathlib import Path

import pytest

from tests.test_request_helper_parse_import_boundary import REQUEST_HELPER_MODULES

pytestmark = pytest.mark.architecture


EXPLICIT_AGENT_HELPER_MODULES = (
    "hyperbrowser/client/managers/agent_start_utils.py",
    "hyperbrowser/client/managers/agent_stop_utils.py",
    "hyperbrowser/client/managers/agent_task_read_utils.py",
)

EXCLUDED_REQUEST_HELPER_MODULES = {
    "hyperbrowser/client/managers/model_request_utils.py",
}


def test_request_helper_parse_import_boundary_inventory_stays_in_sync():
    discovered_request_helper_modules = sorted(
        module_path.as_posix()
        for module_path in Path("hyperbrowser/client/managers").glob("*_request_utils.py")
        if module_path.as_posix() not in EXCLUDED_REQUEST_HELPER_MODULES
    )
    expected_modules = sorted(
        [
            *discovered_request_helper_modules,
            *EXPLICIT_AGENT_HELPER_MODULES,
        ]
    )

    assert sorted(REQUEST_HELPER_MODULES) == expected_modules
