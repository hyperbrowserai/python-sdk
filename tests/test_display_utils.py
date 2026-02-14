from hyperbrowser.display_utils import normalize_display_text


def test_normalize_display_text_keeps_valid_input():
    assert normalize_display_text("hello", max_length=20) == "hello"


def test_normalize_display_text_replaces_control_characters_and_trims():
    assert (
        normalize_display_text(" \nhello\tworld\r ", max_length=50)
        == "?hello?world?"
    )


def test_normalize_display_text_truncates_long_values():
    assert (
        normalize_display_text("abcdefghij", max_length=7) == "... (truncated)"
    )


def test_normalize_display_text_returns_empty_for_unreadable_inputs():
    class _BrokenString(str):
        def __iter__(self):  # type: ignore[override]
            raise RuntimeError("cannot iterate")

    assert normalize_display_text(_BrokenString("value"), max_length=20) == ""


def test_normalize_display_text_returns_empty_for_non_string_inputs():
    assert normalize_display_text(123, max_length=20) == ""  # type: ignore[arg-type]
