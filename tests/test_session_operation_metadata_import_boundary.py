from pathlib import Path

import pytest

from tests.test_session_operation_metadata_usage import MODULES as MANAGER_MODULES
from tests.test_session_upload_metadata_usage import MODULE_PATH as UPLOAD_HELPER_MODULE

pytestmark = pytest.mark.architecture


EXPECTED_EXTRA_IMPORTERS = (
    "tests/test_session_operation_metadata.py",
    "tests/test_session_operation_metadata_import_boundary.py",
    "tests/test_session_operation_metadata_usage.py",
    "tests/test_session_upload_metadata_usage.py",
)


def test_session_operation_metadata_imports_are_centralized():
    discovered_modules: list[str] = []

    for module_path in sorted(Path("hyperbrowser").rglob("*.py")):
        module_text = module_path.read_text(encoding="utf-8")
        if "session_operation_metadata import" in module_text:
            discovered_modules.append(module_path.as_posix())

    for module_path in sorted(Path("tests").glob("test_*.py")):
        module_text = module_path.read_text(encoding="utf-8")
        if "session_operation_metadata import" in module_text:
            discovered_modules.append(module_path.as_posix())

    expected_modules = sorted([*MANAGER_MODULES, UPLOAD_HELPER_MODULE, *EXPECTED_EXTRA_IMPORTERS])
    assert discovered_modules == expected_modules
