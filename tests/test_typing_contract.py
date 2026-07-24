import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Set


ROOT = Path(__file__).resolve().parents[1]
TYPECHECK_DIR = ROOT / "tests" / "typecheck"


def _run_mypy(fixture: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "mypy",
            "--python-version=3.8",
            "--follow-imports=silent",
            "--no-site-packages",
            "--ignore-missing-imports",
            "--check-untyped-defs",
            "--show-error-codes",
            "--no-error-summary",
            "--no-pretty",
            "--no-incremental",
            str(TYPECHECK_DIR / fixture),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def _run_pyright(fixture: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "pyright",
            "--outputjson",
            "--pythonpath",
            sys.executable,
            str(TYPECHECK_DIR / fixture),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def _expected_error_lines(path: Path, marker: str) -> Set[int]:
    return {
        line_number
        for line_number, line in enumerate(path.read_text().splitlines(), start=1)
        if "#" in line
        and marker in {item.strip() for item in line.split("#", 1)[1].split(",")}
    }


def _actual_error_lines(output: str) -> Set[int]:
    return {
        int(line_number) for line_number in re.findall(r"(?m)^.*:(\d+): error:", output)
    }


def _actual_pyright_error_lines(output: str) -> Set[int]:
    report = json.loads(output)
    return {
        diagnostic["range"]["start"]["line"] + 1
        for diagnostic in report["generalDiagnostics"]
        if diagnostic["severity"] == "error"
    }


def test_valid_typed_dict_and_legacy_request_calls_typecheck() -> None:
    result = _run_mypy("valid_requests.py")

    assert result.returncode == 0, result.stdout


def test_valid_typed_dict_and_legacy_request_calls_typecheck_with_pyright() -> None:
    result = _run_pyright("valid_requests.py")

    assert result.returncode == 0, result.stdout


def test_invalid_inline_request_keys_and_values_are_rejected() -> None:
    fixture = TYPECHECK_DIR / "invalid_requests.py"
    result = _run_mypy(fixture.name)

    assert result.returncode == 1, result.stdout
    assert _actual_error_lines(result.stdout) == _expected_error_lines(fixture, "M"), (
        result.stdout
    )


def test_invalid_requests_are_rejected_on_the_same_lines_by_pyright() -> None:
    fixture = TYPECHECK_DIR / "invalid_requests.py"
    result = _run_pyright(fixture.name)

    assert result.returncode == 1, result.stdout
    assert _actual_pyright_error_lines(result.stdout) == _expected_error_lines(
        fixture, "P"
    ), result.stdout
