from pathlib import Path


def test_makefile_defines_architecture_check_target():
    makefile_text = Path("Makefile").read_text(encoding="utf-8")

    assert "architecture-check:" in makefile_text
    assert "tests/test_manager_model_dump_usage.py" in makefile_text
    assert "tests/test_ci_workflow_quality_gates.py" in makefile_text


def test_makefile_check_target_includes_architecture_checks():
    makefile_text = Path("Makefile").read_text(encoding="utf-8")

    assert "check: lint format-check compile architecture-check test build" in makefile_text
