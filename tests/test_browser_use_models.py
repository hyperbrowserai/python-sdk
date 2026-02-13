from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.models.agents.browser_use import cast_steps_for_version


def test_cast_steps_for_version_latest_returns_original_steps():
    steps = [{"state": "kept-as-is"}]

    result = cast_steps_for_version(steps, "latest")

    assert result is steps


def test_cast_steps_for_version_raises_hyperbrowser_error_for_invalid_version():
    steps = [{"state": "ignored"}]

    try:
        cast_steps_for_version(steps, "v999")  # type: ignore[arg-type]
    except HyperbrowserError as exc:
        assert "Invalid browser-use version" in str(exc)
    else:
        raise AssertionError("Expected HyperbrowserError for invalid version")
