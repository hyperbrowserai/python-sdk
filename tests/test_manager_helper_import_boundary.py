from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


MANAGER_DIRECTORIES = (
    Path("hyperbrowser/client/managers/sync_manager"),
    Path("hyperbrowser/client/managers/async_manager"),
)

DISALLOWED_IMPORT_MARKERS = (
    "response_utils import",
    "session_utils import",
)


def test_managers_do_not_import_low_level_parse_modules():
    violating_modules: list[str] = []
    for manager_dir in MANAGER_DIRECTORIES:
        for module_path in sorted(manager_dir.glob("*.py")):
            module_text = module_path.read_text(encoding="utf-8")
            if any(marker in module_text for marker in DISALLOWED_IMPORT_MARKERS):
                violating_modules.append(module_path.as_posix())

        for nested_dir in sorted(
            path for path in manager_dir.iterdir() if path.is_dir()
        ):
            for module_path in sorted(nested_dir.glob("*.py")):
                module_text = module_path.read_text(encoding="utf-8")
                if any(marker in module_text for marker in DISALLOWED_IMPORT_MARKERS):
                    violating_modules.append(module_path.as_posix())

    assert violating_modules == []
