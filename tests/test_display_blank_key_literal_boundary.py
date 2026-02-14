from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


HYPERBROWSER_ROOT = Path(__file__).resolve().parents[1] / "hyperbrowser"
ALLOWED_LITERAL_MODULE = Path("display_utils.py")
BLANK_KEY_LITERAL = "<blank key>"


def test_blank_key_literal_is_centralized_in_display_utils():
    violations: list[str] = []

    for module_path in sorted(HYPERBROWSER_ROOT.rglob("*.py")):
        relative_path = module_path.relative_to(HYPERBROWSER_ROOT)
        if relative_path == ALLOWED_LITERAL_MODULE:
            continue
        module_text = module_path.read_text(encoding="utf-8")
        if BLANK_KEY_LITERAL not in module_text:
            continue
        violations.append(relative_path.as_posix())

    assert violations == []
