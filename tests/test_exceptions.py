from hyperbrowser.exceptions import HyperbrowserError


def test_hyperbrowser_error_str_includes_zero_status_code():
    error = HyperbrowserError("request failed", status_code=0)

    assert str(error) == "request failed - Status: 0"


def test_hyperbrowser_error_str_includes_original_error_details_once():
    root_cause = ValueError("boom")
    error = HyperbrowserError("request failed", original_error=root_cause)

    assert str(error) == "request failed - Caused by ValueError: boom"
