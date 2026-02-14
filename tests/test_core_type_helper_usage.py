import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


CORE_MODULES = (
    "hyperbrowser/config.py",
    "hyperbrowser/header_utils.py",
    "hyperbrowser/client/base.py",
    "hyperbrowser/client/file_utils.py",
    "hyperbrowser/client/polling.py",
    "hyperbrowser/models/session.py",
    "hyperbrowser/transport/base.py",
    "hyperbrowser/transport/sync.py",
    "hyperbrowser/transport/async_transport.py",
    "hyperbrowser/transport/error_utils.py",
    "hyperbrowser/mapping_utils.py",
    "hyperbrowser/client/managers/response_utils.py",
    "hyperbrowser/client/managers/extension_utils.py",
    "hyperbrowser/client/managers/list_parsing_utils.py",
    "hyperbrowser/client/managers/sync_manager/computer_action.py",
    "hyperbrowser/client/managers/async_manager/computer_action.py",
    "hyperbrowser/client/managers/sync_manager/session.py",
    "hyperbrowser/client/managers/async_manager/session.py",
    "hyperbrowser/client/managers/computer_action_utils.py",
    "hyperbrowser/client/managers/session_upload_utils.py",
    "hyperbrowser/client/managers/web_payload_utils.py",
    "hyperbrowser/tools/__init__.py",
    "hyperbrowser/display_utils.py",
    "hyperbrowser/exceptions.py",
)

_PLAIN_TYPE_CHECK_PATTERN = re.compile(
    r"type\s*\([^)]*\)\s+is(?:\s+not)?\s+(?:str|int)"
)


def test_core_modules_use_shared_plain_type_helpers():
    violations: list[str] = []
    for module_path in CORE_MODULES:
        module_text = Path(module_path).read_text(encoding="utf-8")
        for line_number, line_text in enumerate(module_text.splitlines(), start=1):
            if _PLAIN_TYPE_CHECK_PATTERN.search(line_text):
                violations.append(f"{module_path}:{line_number}")

    assert violations == []
