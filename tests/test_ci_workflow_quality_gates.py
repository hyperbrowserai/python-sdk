from pathlib import Path


def test_ci_workflow_includes_architecture_guard_job():
    ci_workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "architecture-guards:" in ci_workflow
    assert "run: make architecture-check" in ci_workflow


def test_ci_workflow_uses_make_targets_for_quality_gates():
    ci_workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "run: make lint" in ci_workflow
    assert "run: make format-check" in ci_workflow
    assert "run: make compile" in ci_workflow
    assert "run: make test" in ci_workflow
    assert "run: make build" in ci_workflow
