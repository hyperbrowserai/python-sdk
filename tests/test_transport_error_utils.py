import httpx

from hyperbrowser.transport.error_utils import (
    extract_request_error_context,
    format_request_failure_message,
)


class _BrokenRequest:
    @property
    def method(self) -> str:
        raise ValueError("missing method")

    @property
    def url(self) -> str:
        raise ValueError("missing url")


class _BlankContextRequest:
    method = "   "
    url = "   "


class _RequestErrorWithFailingRequestProperty(httpx.RequestError):
    @property
    def request(self):  # type: ignore[override]
        raise ValueError("broken request property")


class _RequestErrorWithBrokenRequest(httpx.RequestError):
    @property
    def request(self):  # type: ignore[override]
        return _BrokenRequest()


class _RequestErrorWithBlankContext(httpx.RequestError):
    @property
    def request(self):  # type: ignore[override]
        return _BlankContextRequest()


def test_extract_request_error_context_uses_unknown_when_request_unset():
    method, url = extract_request_error_context(httpx.RequestError("network down"))

    assert method == "UNKNOWN"
    assert url == "unknown URL"


def test_extract_request_error_context_handles_request_property_failures():
    method, url = extract_request_error_context(
        _RequestErrorWithFailingRequestProperty("network down")
    )

    assert method == "UNKNOWN"
    assert url == "unknown URL"


def test_extract_request_error_context_handles_broken_request_attributes():
    method, url = extract_request_error_context(
        _RequestErrorWithBrokenRequest("network down")
    )

    assert method == "UNKNOWN"
    assert url == "unknown URL"


def test_extract_request_error_context_normalizes_blank_method_and_url():
    method, url = extract_request_error_context(
        _RequestErrorWithBlankContext("network down")
    )

    assert method == "UNKNOWN"
    assert url == "unknown URL"


def test_format_request_failure_message_uses_fallback_values():
    message = format_request_failure_message(
        httpx.RequestError("network down"),
        fallback_method="GET",
        fallback_url="https://example.com/fallback",
    )

    assert message == "Request GET https://example.com/fallback failed"


def test_format_request_failure_message_prefers_request_context():
    request = httpx.Request("POST", "https://example.com/actual")
    message = format_request_failure_message(
        httpx.RequestError("network down", request=request),
        fallback_method="GET",
        fallback_url="https://example.com/fallback",
    )

    assert message == "Request POST https://example.com/actual failed"
