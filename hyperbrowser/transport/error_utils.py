import json
import re
from typing import Any

import httpx

_HTTP_METHOD_TOKEN_PATTERN = re.compile(r"^[!#$%&'*+\-.^_`|~0-9A-Z]+$")
_NUMERIC_LIKE_URL_PATTERN = re.compile(
    r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$"
)
_MAX_ERROR_MESSAGE_LENGTH = 2000
_MAX_REQUEST_URL_DISPLAY_LENGTH = 1000
_MAX_REQUEST_METHOD_LENGTH = 50
_INVALID_URL_SENTINELS = {
    "none",
    "null",
    "undefined",
    "nan",
    "inf",
    "+inf",
    "-inf",
    "infinity",
    "+infinity",
    "-infinity",
}


def _normalize_request_method(method: Any) -> str:
    if not isinstance(method, str) or not method.strip():
        return "UNKNOWN"
    normalized_method = method.strip().upper()
    if len(normalized_method) > _MAX_REQUEST_METHOD_LENGTH:
        return "UNKNOWN"
    if not _HTTP_METHOD_TOKEN_PATTERN.fullmatch(normalized_method):
        return "UNKNOWN"
    return normalized_method


def _normalize_request_url(url: Any) -> str:
    if url is None:
        return "unknown URL"
    if isinstance(url, bool):
        return "unknown URL"
    raw_url = url
    if isinstance(raw_url, (bytes, bytearray, memoryview)):
        try:
            raw_url = memoryview(raw_url).tobytes().decode("utf-8")
        except (TypeError, ValueError, UnicodeDecodeError):
            return "unknown URL"
    elif not isinstance(raw_url, str):
        try:
            raw_url = str(raw_url)
        except Exception:
            return "unknown URL"

    normalized_url = raw_url.strip()
    if not normalized_url:
        return "unknown URL"
    lowered_url = normalized_url.lower()
    if lowered_url in _INVALID_URL_SENTINELS or _NUMERIC_LIKE_URL_PATTERN.fullmatch(
        normalized_url
    ):
        return "unknown URL"
    if any(character.isspace() for character in normalized_url):
        return "unknown URL"
    if any(
        ord(character) < 32 or ord(character) == 127 for character in normalized_url
    ):
        return "unknown URL"
    if len(normalized_url) > _MAX_REQUEST_URL_DISPLAY_LENGTH:
        return f"{normalized_url[:_MAX_REQUEST_URL_DISPLAY_LENGTH]}... (truncated)"
    return normalized_url


def _truncate_error_message(message: str) -> str:
    if len(message) <= _MAX_ERROR_MESSAGE_LENGTH:
        return message
    return f"{message[:_MAX_ERROR_MESSAGE_LENGTH]}... (truncated)"


def _stringify_error_value(value: Any, *, _depth: int = 0) -> str:
    if _depth > 10:
        return str(value)
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("message", "error", "detail", "errors", "msg", "title", "reason"):
            nested_value = value.get(key)
            if nested_value is not None:
                return _stringify_error_value(nested_value, _depth=_depth + 1)
    if isinstance(value, (list, tuple)):
        max_list_items = 10
        collected_messages = [
            item_message
            for item_message in (
                _stringify_error_value(item, _depth=_depth + 1)
                for item in value[:max_list_items]
            )
            if item_message
        ]
        if collected_messages:
            joined_messages = (
                collected_messages[0]
                if len(collected_messages) == 1
                else "; ".join(collected_messages)
            )
            remaining_items = len(value) - max_list_items
            if remaining_items > 0:
                return f"{joined_messages}; ... (+{remaining_items} more)"
            return joined_messages
    try:
        return json.dumps(value, sort_keys=True)
    except (TypeError, ValueError, RecursionError):
        return str(value)


def extract_error_message(response: httpx.Response, fallback_error: Exception) -> str:
    def _fallback_message() -> str:
        response_text = response.text
        if isinstance(response_text, str) and response_text.strip():
            return _truncate_error_message(response_text)
        return _truncate_error_message(str(fallback_error))

    try:
        error_data: Any = response.json()
    except Exception:
        return _fallback_message()

    extracted_message: str
    if isinstance(error_data, dict):
        for key in ("message", "error", "detail", "errors", "title", "reason"):
            message = error_data.get(key)
            if message is not None:
                candidate_message = _stringify_error_value(message)
                if candidate_message.strip():
                    extracted_message = candidate_message
                    break
        else:
            extracted_message = _stringify_error_value(error_data)
    elif isinstance(error_data, str):
        extracted_message = error_data
    else:
        extracted_message = _stringify_error_value(error_data)

    if not extracted_message.strip():
        return _fallback_message()
    return _truncate_error_message(extracted_message)


def extract_request_error_context(error: httpx.RequestError) -> tuple[str, str]:
    try:
        request = error.request
    except Exception:
        request = None
    if request is None:
        return "UNKNOWN", "unknown URL"
    try:
        request_method = request.method
    except Exception:
        request_method = "UNKNOWN"
    request_method = _normalize_request_method(request_method)

    try:
        request_url = str(request.url)
    except Exception:
        request_url = "unknown URL"
    request_url = _normalize_request_url(request_url)
    return request_method, request_url


def format_request_failure_message(
    error: httpx.RequestError, *, fallback_method: object, fallback_url: object
) -> str:
    request_method, request_url = extract_request_error_context(error)
    effective_method = (
        request_method if request_method != "UNKNOWN" else fallback_method
    )
    effective_method = _normalize_request_method(effective_method)

    effective_url = request_url if request_url != "unknown URL" else fallback_url
    effective_url = _normalize_request_url(effective_url)
    return f"Request {effective_method} {effective_url} failed"


def format_generic_request_failure_message(*, method: object, url: object) -> str:
    normalized_method = _normalize_request_method(method)
    normalized_url = _normalize_request_url(url)
    return f"Request {normalized_method} {normalized_url} failed"
