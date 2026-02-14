from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


MANAGER_DIRECTORIES = (
    Path("hyperbrowser/client/managers/sync_manager"),
    Path("hyperbrowser/client/managers/async_manager"),
)

DISALLOWED_PARSE_MARKERS = (
    "parse_response_model(",
    "parse_session_response_model(",
    "parse_session_recordings_response_data(",
)


def test_managers_route_parsing_through_shared_helpers():
    violating_modules: list[str] = []
    for manager_dir in MANAGER_DIRECTORIES:
        for module_path in sorted(manager_dir.glob("*.py")):
            module_text = module_path.read_text(encoding="utf-8")
            if any(marker in module_text for marker in DISALLOWED_PARSE_MARKERS):
                violating_modules.append(module_path.as_posix())

        for nested_dir in sorted(
            path for path in manager_dir.iterdir() if path.is_dir()
        ):
            for module_path in sorted(nested_dir.glob("*.py")):
                module_text = module_path.read_text(encoding="utf-8")
                if any(marker in module_text for marker in DISALLOWED_PARSE_MARKERS):
                    violating_modules.append(module_path.as_posix())

    assert violating_modules == []
