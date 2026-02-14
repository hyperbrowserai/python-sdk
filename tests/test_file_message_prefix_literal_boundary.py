from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


HYPERBROWSER_ROOT = Path(__file__).resolve().parents[1] / "hyperbrowser"
ALLOWED_LITERAL_MODULES = {
    Path("client/managers/extension_operation_metadata.py"),
    Path("client/managers/session_operation_metadata.py"),
}
FORBIDDEN_PREFIX_LITERALS = (
    "Extension file not found at path",
    "Extension file path must point to a file",
    "Failed to open extension file at path",
    "Upload file not found at path",
    "Upload file path must point to a file",
    "Failed to open upload file at path",
)


def test_file_message_prefix_literals_are_centralized_in_metadata_modules():
    violations: list[str] = []

    for module_path in sorted(HYPERBROWSER_ROOT.rglob("*.py")):
        relative_path = module_path.relative_to(HYPERBROWSER_ROOT)
        if relative_path in ALLOWED_LITERAL_MODULES:
            continue
        module_text = module_path.read_text(encoding="utf-8")
        for literal in FORBIDDEN_PREFIX_LITERALS:
            if literal in module_text:
                violations.append(f"{relative_path}:{literal}")

    assert violations == []
