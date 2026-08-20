import json
from pathlib import Path

import pytest

from hyperbrowser.client.managers.sandboxes import image_build
from hyperbrowser.client.managers.sandboxes.dockerfile_analysis import (
    analyze_dockerfile_sources,
)


_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "docker_context_parity.json"
_FIXTURE = json.loads(_FIXTURE_PATH.read_text())


@pytest.mark.parametrize("case", _FIXTURE["dockerfiles"], ids=lambda case: case["name"])
def test_dockerfile_analysis_matches_go_or_falls_back_to_full(case):
    groups, fallback = analyze_dockerfile_sources(case["dockerfile"].encode())

    if case["pythonExpectation"] == "exact":
        assert case["goFallback"] == ""
        assert fallback == ""
        assert groups == case["goSourceGroups"]
    else:
        assert case["pythonExpectation"] == "full"
        assert fallback
        assert groups == []


@pytest.mark.parametrize(
    "case", _FIXTURE["ignoreContexts"], ids=lambda case: case["name"]
)
def test_dockerignore_context_selection_matches_go_fsutil(case, tmp_path):
    for relative in case["files"]:
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        contents = (
            case["dockerignore"] if relative == ".dockerignore" else f"{relative}\n"
        )
        destination.write_text(contents)
    for symlink in case.get("symlinks", []):
        destination = tmp_path / symlink["path"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.symlink_to(symlink["target"])

    ignore_matcher = image_build._load_dockerignore(tmp_path / ".dockerignore")
    entries = image_build._collect_context_entries(
        tmp_path,
        case.get("sources", ["."]),
        ignore_matcher=ignore_matcher,
        required=False,
    )

    assert sorted(entries) == case["expectedEntries"]
