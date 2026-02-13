import httpx

from hyperbrowser.transport.error_utils import (
    extract_error_message,
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


class _DummyResponse:
    def __init__(self, json_value, text: str = "") -> None:
        self._json_value = json_value
        self.text = text

    def json(self):
        return self._json_value


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


def test_format_request_failure_message_normalizes_blank_fallback_values():
    message = format_request_failure_message(
        httpx.RequestError("network down"),
        fallback_method="   ",
        fallback_url="",
    )

    assert message == "Request UNKNOWN unknown URL failed"


def test_extract_error_message_handles_recursive_list_payloads():
    recursive_payload = []
    recursive_payload.append(recursive_payload)
    message = extract_error_message(
        _DummyResponse(recursive_payload), RuntimeError("fallback")
    )

    assert isinstance(message, str)
    assert message


def test_extract_error_message_handles_recursive_dict_payloads():
    recursive_payload = {}
    recursive_payload["message"] = recursive_payload
    message = extract_error_message(
        _DummyResponse(recursive_payload), RuntimeError("fallback")
    )

    assert isinstance(message, str)
    assert message


def test_extract_error_message_uses_fallback_for_blank_dict_message():
    message = extract_error_message(
        _DummyResponse({"message": "   "}), RuntimeError("fallback detail")
    )

    assert message == "fallback detail"


def test_extract_error_message_uses_response_text_for_blank_string_payload():
    message = extract_error_message(
        _DummyResponse("   ", text="raw error body"),
        RuntimeError("fallback detail"),
    )

    assert message == "raw error body"


def test_extract_error_message_extracts_errors_list_messages():
    message = extract_error_message(
        _DummyResponse({"errors": [{"msg": "first issue"}, {"msg": "second issue"}]}),
        RuntimeError("fallback detail"),
    )

    assert message == "first issue; second issue"
