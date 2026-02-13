from hyperbrowser.exceptions import HyperbrowserError


def test_hyperbrowser_error_str_includes_zero_status_code():
    error = HyperbrowserError("request failed", status_code=0)

    assert str(error) == "request failed - Status: 0"


def test_hyperbrowser_error_str_includes_original_error_details_once():
    root_cause = ValueError("boom")
    error = HyperbrowserError("request failed", original_error=root_cause)

    assert str(error) == "request failed - Caused by ValueError: boom"


def test_hyperbrowser_error_str_handles_unstringifiable_original_error():
    class _UnstringifiableError(Exception):
        def __str__(self) -> str:
            raise RuntimeError("cannot stringify")

    error = HyperbrowserError("request failed", original_error=_UnstringifiableError())

    assert (
        str(error)
        == "request failed - Caused by _UnstringifiableError: <unstringifiable _UnstringifiableError>"
    )


def test_hyperbrowser_error_str_sanitizes_control_characters():
    error = HyperbrowserError("bad\trequest\nmessage\x7f")

    assert str(error) == "bad?request?message?"


def test_hyperbrowser_error_str_uses_placeholder_for_blank_message():
    error = HyperbrowserError("   ")

    assert str(error) == "Hyperbrowser error"


def test_hyperbrowser_error_str_truncates_oversized_message():
    error = HyperbrowserError("x" * 2500)

    assert str(error).endswith("... (truncated)")
    assert len(str(error)) <= 2000


def test_hyperbrowser_error_str_truncates_oversized_original_error_message():
    root_cause = ValueError("y" * 2500)
    error = HyperbrowserError("request failed", original_error=root_cause)

    rendered_error = str(error)
    assert "Caused by ValueError:" in rendered_error
    assert rendered_error.endswith("... (truncated)")
