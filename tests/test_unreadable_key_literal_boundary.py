from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


HYPERBROWSER_ROOT = Path(__file__).resolve().parents[1] / "hyperbrowser"
ALLOWED_LITERAL_MODULES = {
    Path("mapping_utils.py"),
    Path("client/managers/extension_utils.py"),
}
UNREADABLE_KEY_LITERAL = "<unreadable key>"


def test_unreadable_key_literal_is_centralized():
    violations: list[str] = []

    for module_path in sorted(HYPERBROWSER_ROOT.rglob("*.py")):
        relative_path = module_path.relative_to(HYPERBROWSER_ROOT)
        if relative_path in ALLOWED_LITERAL_MODULES:
            continue
        module_text = module_path.read_text(encoding="utf-8")
        if UNREADABLE_KEY_LITERAL not in module_text:
            continue
        violations.append(relative_path.as_posix())

    assert violations == []
