from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


HYPERBROWSER_ROOT = Path(__file__).resolve().parents[1] / "hyperbrowser"
ALLOWED_LITERAL_MODULE = Path("client/file_utils.py")
DEFAULT_OPEN_PREFIX_LITERAL = "Failed to open file at path"


def test_default_open_prefix_literal_is_centralized_in_file_utils():
    violations: list[str] = []

    for module_path in sorted(HYPERBROWSER_ROOT.rglob("*.py")):
        relative_path = module_path.relative_to(HYPERBROWSER_ROOT)
        if relative_path == ALLOWED_LITERAL_MODULE:
            continue
        module_text = module_path.read_text(encoding="utf-8")
        if DEFAULT_OPEN_PREFIX_LITERAL not in module_text:
            continue
        violations.append(relative_path.as_posix())

    assert violations == []
