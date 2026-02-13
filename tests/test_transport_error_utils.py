import httpx
import pytest

from hyperbrowser.transport.error_utils import (
    extract_error_message,
    extract_request_error_context,
    format_generic_request_failure_message,
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


class _WhitespaceContextRequest:
    method = "  POST  "
    url = "  https://example.com/trim  "


class _LowercaseMethodRequest:
    method = "get"
    url = "https://example.com/lowercase"


class _TooLongMethodRequest:
    method = "A" * 51
    url = "https://example.com/too-long-method"


class _InvalidMethodTokenRequest:
    method = "GET /invalid"
    url = "https://example.com/invalid-method"


class _MethodLikeRequest:
    class _MethodLike:
        def __str__(self) -> str:
            return "patch"

    method = _MethodLike()
    url = "https://example.com/method-like"


class _WhitespaceInsideUrlRequest:
    method = "GET"
    url = "https://example.com/with space"


class _BytesUrlContextRequest:
    method = "GET"
    url = b"https://example.com/from-bytes"


class _InvalidBytesUrlContextRequest:
    method = "GET"
    url = b"\xff\xfe"


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


class _RequestErrorWithWhitespaceContext(httpx.RequestError):
    @property
    def request(self):  # type: ignore[override]
        return _WhitespaceContextRequest()


class _RequestErrorWithLowercaseMethod(httpx.RequestError):
    @property
    def request(self):  # type: ignore[override]
        return _LowercaseMethodRequest()


class _RequestErrorWithTooLongMethod(httpx.RequestError):
    @property
    def request(self):  # type: ignore[override]
        return _TooLongMethodRequest()


class _RequestErrorWithInvalidMethodToken(httpx.RequestError):
    @property
    def request(self):  # type: ignore[override]
        return _InvalidMethodTokenRequest()


class _RequestErrorWithMethodLikeContext(httpx.RequestError):
    @property
    def request(self):  # type: ignore[override]
        return _MethodLikeRequest()


class _RequestErrorWithWhitespaceInsideUrl(httpx.RequestError):
    @property
    def request(self):  # type: ignore[override]
        return _WhitespaceInsideUrlRequest()


class _RequestErrorWithBytesUrlContext(httpx.RequestError):
    @property
    def request(self):  # type: ignore[override]
        return _BytesUrlContextRequest()


class _RequestErrorWithInvalidBytesUrlContext(httpx.RequestError):
    @property
    def request(self):  # type: ignore[override]
        return _InvalidBytesUrlContextRequest()


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


def test_extract_request_error_context_strips_method_and_url_whitespace():
    method, url = extract_request_error_context(
        _RequestErrorWithWhitespaceContext("network down")
    )

    assert method == "POST"
    assert url == "https://example.com/trim"


def test_extract_request_error_context_normalizes_method_to_uppercase():
    method, url = extract_request_error_context(
        _RequestErrorWithLowercaseMethod("network down")
    )

    assert method == "GET"
    assert url == "https://example.com/lowercase"


def test_extract_request_error_context_rejects_overlong_methods():
    method, url = extract_request_error_context(
        _RequestErrorWithTooLongMethod("network down")
    )

    assert method == "UNKNOWN"
    assert url == "https://example.com/too-long-method"


def test_extract_request_error_context_rejects_invalid_method_tokens():
    method, url = extract_request_error_context(
        _RequestErrorWithInvalidMethodToken("network down")
    )

    assert method == "UNKNOWN"
    assert url == "https://example.com/invalid-method"


def test_extract_request_error_context_accepts_stringifiable_method_values():
    method, url = extract_request_error_context(
        _RequestErrorWithMethodLikeContext("network down")
    )

    assert method == "PATCH"
    assert url == "https://example.com/method-like"


def test_extract_request_error_context_rejects_urls_with_whitespace():
    method, url = extract_request_error_context(
        _RequestErrorWithWhitespaceInsideUrl("network down")
    )

    assert method == "GET"
    assert url == "unknown URL"


def test_extract_request_error_context_supports_bytes_url_values():
    method, url = extract_request_error_context(
        _RequestErrorWithBytesUrlContext("network down")
    )

    assert method == "GET"
    assert url == "https://example.com/from-bytes"


def test_extract_request_error_context_rejects_invalid_bytes_url_values():
    method, url = extract_request_error_context(
        _RequestErrorWithInvalidBytesUrlContext("network down")
    )

    assert method == "GET"
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


def test_format_request_failure_message_normalizes_lowercase_fallback_method():
    message = format_request_failure_message(
        httpx.RequestError("network down"),
        fallback_method="post",
        fallback_url="https://example.com/fallback",
    )

    assert message == "Request POST https://example.com/fallback failed"


def test_format_request_failure_message_rejects_overlong_fallback_methods():
    message = format_request_failure_message(
        httpx.RequestError("network down"),
        fallback_method="A" * 51,
        fallback_url="https://example.com/fallback",
    )

    assert message == "Request UNKNOWN https://example.com/fallback failed"


def test_format_request_failure_message_normalizes_non_string_fallback_values():
    message = format_request_failure_message(
        httpx.RequestError("network down"),
        fallback_method=123,
        fallback_url=object(),
    )

    assert message == "Request UNKNOWN unknown URL failed"


@pytest.mark.parametrize("sentinel_method", ["null", "undefined", "true", "false"])
def test_format_request_failure_message_normalizes_sentinel_fallback_methods(
    sentinel_method: str,
):
    message = format_request_failure_message(
        httpx.RequestError("network down"),
        fallback_method=sentinel_method,
        fallback_url="https://example.com/fallback",
    )

    assert message == "Request UNKNOWN https://example.com/fallback failed"


@pytest.mark.parametrize("numeric_like_method", ["1", "1.5", "-1.25", "+2", ".75", "1e3"])
def test_format_request_failure_message_normalizes_numeric_like_fallback_methods(
    numeric_like_method: str,
):
    message = format_request_failure_message(
        httpx.RequestError("network down"),
        fallback_method=numeric_like_method,
        fallback_url="https://example.com/fallback",
    )

    assert message == "Request UNKNOWN https://example.com/fallback failed"


def test_format_request_failure_message_supports_ascii_bytes_method_values():
    message = format_request_failure_message(
        httpx.RequestError("network down"),
        fallback_method=b"post",
        fallback_url="https://example.com/fallback",
    )

    assert message == "Request POST https://example.com/fallback failed"


def test_format_request_failure_message_normalizes_invalid_bytes_method_values():
    message = format_request_failure_message(
        httpx.RequestError("network down"),
        fallback_method=b"\xff\xfe",
        fallback_url="https://example.com/fallback",
    )

    assert message == "Request UNKNOWN https://example.com/fallback failed"


def test_format_request_failure_message_normalizes_numeric_fallback_url_values():
    message = format_request_failure_message(
        httpx.RequestError("network down"),
        fallback_method="GET",
        fallback_url=123,
    )

    assert message == "Request GET unknown URL failed"


def test_format_request_failure_message_normalizes_boolean_fallback_url_values():
    message = format_request_failure_message(
        httpx.RequestError("network down"),
        fallback_method="GET",
        fallback_url=True,
    )

    assert message == "Request GET unknown URL failed"


@pytest.mark.parametrize(
    "sentinel_url",
    [
        "none",
        "null",
        "undefined",
        "true",
        "false",
        "nan",
        "inf",
        "+inf",
        "-inf",
        "infinity",
        "+infinity",
        "-infinity",
    ],
)
def test_format_request_failure_message_normalizes_sentinel_fallback_url_values(
    sentinel_url: str,
):
    message = format_request_failure_message(
        httpx.RequestError("network down"),
        fallback_method="GET",
        fallback_url=sentinel_url,
    )

    assert message == "Request GET unknown URL failed"


@pytest.mark.parametrize("numeric_like_url", ["1", "1.5", "-1.25", "+2", ".75", "1e3"])
def test_format_request_failure_message_normalizes_numeric_like_url_strings(
    numeric_like_url: str,
):
    message = format_request_failure_message(
        httpx.RequestError("network down"),
        fallback_method="GET",
        fallback_url=numeric_like_url,
    )

    assert message == "Request GET unknown URL failed"


def test_format_request_failure_message_supports_url_like_fallback_values():
    message = format_request_failure_message(
        httpx.RequestError("network down"),
        fallback_method="GET",
        fallback_url=httpx.URL("https://example.com/fallback"),
    )

    assert message == "Request GET https://example.com/fallback failed"


def test_format_request_failure_message_supports_utf8_bytes_fallback_values():
    message = format_request_failure_message(
        httpx.RequestError("network down"),
        fallback_method="GET",
        fallback_url=b"https://example.com/bytes",
    )

    assert message == "Request GET https://example.com/bytes failed"


def test_format_request_failure_message_normalizes_invalid_bytes_fallback_values():
    message = format_request_failure_message(
        httpx.RequestError("network down"),
        fallback_method="GET",
        fallback_url=b"\xff\xfe\xfd",
    )

    assert message == "Request GET unknown URL failed"


def test_format_generic_request_failure_message_normalizes_invalid_url_objects():
    message = format_generic_request_failure_message(
        method="GET",
        url=object(),
    )

    assert message == "Request GET unknown URL failed"


def test_format_generic_request_failure_message_normalizes_numeric_url_values():
    message = format_generic_request_failure_message(
        method="GET",
        url=123,
    )

    assert message == "Request GET unknown URL failed"


def test_format_generic_request_failure_message_normalizes_boolean_url_values():
    message = format_generic_request_failure_message(
        method="GET",
        url=False,
    )

    assert message == "Request GET unknown URL failed"


@pytest.mark.parametrize(
    "sentinel_url",
    [
        "none",
        "null",
        "undefined",
        "true",
        "false",
        "nan",
        "inf",
        "+inf",
        "-inf",
        "infinity",
        "+infinity",
        "-infinity",
    ],
)
def test_format_generic_request_failure_message_normalizes_sentinel_url_values(
    sentinel_url: str,
):
    message = format_generic_request_failure_message(
        method="GET",
        url=sentinel_url,
    )

    assert message == "Request GET unknown URL failed"


@pytest.mark.parametrize("numeric_like_url", ["1", "1.5", "-1.25", "+2", ".75", "1e3"])
def test_format_generic_request_failure_message_normalizes_numeric_like_url_strings(
    numeric_like_url: str,
):
    message = format_generic_request_failure_message(
        method="GET",
        url=numeric_like_url,
    )

    assert message == "Request GET unknown URL failed"


def test_format_generic_request_failure_message_supports_url_like_values():
    message = format_generic_request_failure_message(
        method="GET",
        url=httpx.URL("https://example.com/path"),
    )

    assert message == "Request GET https://example.com/path failed"


def test_format_generic_request_failure_message_supports_utf8_memoryview_urls():
    message = format_generic_request_failure_message(
        method="GET",
        url=memoryview(b"https://example.com/memoryview"),
    )

    assert message == "Request GET https://example.com/memoryview failed"


def test_format_generic_request_failure_message_normalizes_invalid_method_values():
    message = format_generic_request_failure_message(
        method="GET /invalid",
        url="https://example.com/path",
    )

    assert message == "Request UNKNOWN https://example.com/path failed"


def test_format_generic_request_failure_message_normalizes_non_string_method_values():
    message = format_generic_request_failure_message(
        method=123,
        url="https://example.com/path",
    )

    assert message == "Request UNKNOWN https://example.com/path failed"


@pytest.mark.parametrize("sentinel_method", ["null", "undefined", "true", "false"])
def test_format_generic_request_failure_message_normalizes_sentinel_method_values(
    sentinel_method: str,
):
    message = format_generic_request_failure_message(
        method=sentinel_method,
        url="https://example.com/path",
    )

    assert message == "Request UNKNOWN https://example.com/path failed"


@pytest.mark.parametrize("numeric_like_method", ["1", "1.5", "-1.25", "+2", ".75", "1e3"])
def test_format_generic_request_failure_message_normalizes_numeric_like_method_values(
    numeric_like_method: str,
):
    message = format_generic_request_failure_message(
        method=numeric_like_method,
        url="https://example.com/path",
    )

    assert message == "Request UNKNOWN https://example.com/path failed"


def test_format_generic_request_failure_message_supports_stringifiable_method_values():
    class _MethodLike:
        def __str__(self) -> str:
            return "delete"

    message = format_generic_request_failure_message(
        method=_MethodLike(),
        url="https://example.com/path",
    )

    assert message == "Request DELETE https://example.com/path failed"


def test_format_generic_request_failure_message_supports_memoryview_method_values():
    message = format_generic_request_failure_message(
        method=memoryview(b"patch"),
        url="https://example.com/path",
    )

    assert message == "Request PATCH https://example.com/path failed"


def test_format_request_failure_message_truncates_very_long_fallback_urls():
    very_long_url = "https://example.com/" + ("a" * 1200)
    message = format_request_failure_message(
        httpx.RequestError("network down"),
        fallback_method="GET",
        fallback_url=very_long_url,
    )

    assert "Request GET https://example.com/" in message
    assert "... (truncated) failed" in message


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


def test_extract_error_message_uses_fallback_error_when_response_text_is_blank():
    message = extract_error_message(
        _DummyResponse("   ", text="   "),
        RuntimeError("fallback detail"),
    )

    assert message == "fallback detail"


def test_extract_error_message_extracts_errors_list_messages():
    message = extract_error_message(
        _DummyResponse({"errors": [{"msg": "first issue"}, {"msg": "second issue"}]}),
        RuntimeError("fallback detail"),
    )

    assert message == "first issue; second issue"


def test_extract_error_message_uses_title_field_when_present():
    message = extract_error_message(
        _DummyResponse({"title": "Request validation failed"}),
        RuntimeError("fallback detail"),
    )

    assert message == "Request validation failed"


def test_extract_error_message_uses_reason_field_when_present():
    message = extract_error_message(
        _DummyResponse({"reason": "service temporarily unavailable"}),
        RuntimeError("fallback detail"),
    )

    assert message == "service temporarily unavailable"


def test_extract_error_message_truncates_long_errors_lists():
    errors_payload = {"errors": [{"msg": f"issue-{index}"} for index in range(12)]}
    message = extract_error_message(
        _DummyResponse(errors_payload),
        RuntimeError("fallback detail"),
    )

    assert "issue-0" in message
    assert "issue-9" in message
    assert "issue-10" not in message
    assert "... (+2 more)" in message


def test_extract_error_message_skips_blank_message_and_uses_detail():
    message = extract_error_message(
        _DummyResponse({"message": "   ", "detail": "useful detail"}),
        RuntimeError("fallback detail"),
    )

    assert message == "useful detail"


def test_extract_error_message_truncates_extracted_messages():
    large_message = "x" * 2100
    message = extract_error_message(
        _DummyResponse({"message": large_message}),
        RuntimeError("fallback detail"),
    )

    assert message.endswith("... (truncated)")
    assert len(message) < len(large_message)


def test_extract_error_message_truncates_fallback_response_text():
    large_response_text = "y" * 2100
    message = extract_error_message(
        _DummyResponse("   ", text=large_response_text),
        RuntimeError("fallback detail"),
    )

    assert message.endswith("... (truncated)")
    assert len(message) < len(large_response_text)
