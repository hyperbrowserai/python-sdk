import asyncio

import httpx
import pytest

from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.sandbox_common import normalize_network_error, request_context


@pytest.mark.parametrize(
    "error",
    [
        asyncio.CancelledError(),
        KeyboardInterrupt(),
        SystemExit(),
    ],
)
def test_control_flow_exceptions_propagate_instead_of_becoming_network_errors(error):
    with pytest.raises(type(error)) as exc_info:
        normalize_network_error(error, "control", "Unknown error occurred")

    assert exc_info.value is error


def test_transport_error_without_a_message_reports_its_type():
    error = normalize_network_error(
        httpx.ReadTimeout(""),
        "control",
        "Unknown error occurred",
    )

    assert isinstance(error, HyperbrowserError)
    assert str(error) == "Unknown error occurred (ReadTimeout)"
    assert error.retryable is True


def test_transport_error_with_a_message_keeps_its_detail():
    error = normalize_network_error(
        httpx.ConnectError("connection refused"),
        "control",
        "Unknown error occurred",
    )

    assert str(error) == "connection refused"


def test_request_context_is_appended_so_the_failing_call_is_identifiable():
    error = normalize_network_error(
        httpx.ReadTimeout(""),
        "control",
        "Unknown error occurred",
        request_context("post", "/sandbox"),
    )

    assert str(error) == "Unknown error occurred (ReadTimeout) [POST /sandbox]"


@pytest.mark.parametrize(
    ("method", "target", "expected"),
    [
        ("GET", "/images/builds/abc", "[GET /images/builds/abc]"),
        ("GET", "https://api.hyperbrowser.ai/sandbox?token=secret", "[GET /sandbox]"),
        ("GET", "/sandbox?token=secret", "[GET /sandbox]"),
        ("", "/sandbox", "[/sandbox]"),
        ("GET", "", "[GET]"),
        ("", "", ""),
    ],
)
def test_request_context_drops_query_strings_and_hosts(method, target, expected):
    assert request_context(method, target) == expected
