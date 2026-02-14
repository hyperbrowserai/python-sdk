import json
from numbers import Real
import re
from collections.abc import Mapping
from typing import Any

import httpx

_HTTP_METHOD_TOKEN_PATTERN = re.compile(r"^[!#$%&'*+\-.^_`|~0-9A-Z]+$")
_NUMERIC_LIKE_URL_PATTERN = re.compile(
    r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$"
)
_NUMERIC_LIKE_METHOD_PATTERN = re.compile(
    r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$"
)
_MAX_ERROR_MESSAGE_LENGTH = 2000
_MAX_REQUEST_URL_DISPLAY_LENGTH = 1000
_MAX_REQUEST_METHOD_LENGTH = 50
_INVALID_METHOD_SENTINELS = {
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
}
_INVALID_URL_SENTINELS = {
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
}


def _safe_to_string(value: Any) -> str:
    try:
        normalized_value = str(value)
    except Exception:
        return f"<unstringifiable {type(value).__name__}>"
    if type(normalized_value) is not str:
        return f"<{type(value).__name__}>"
    try:
        sanitized_value = "".join(
            "?" if ord(character) < 32 or ord(character) == 127 else character
            for character in normalized_value
        )
        if type(sanitized_value) is not str:
            return f"<{type(value).__name__}>"
        if sanitized_value.strip():
            return sanitized_value
    except Exception:
        return f"<{type(value).__name__}>"
    return f"<{type(value).__name__}>"


def _sanitize_error_message_text(message: str) -> str:
    try:
        return "".join(
            "?" if ord(character) < 32 or ord(character) == 127 else character
            for character in message
        )
    except Exception:
        return _safe_to_string(message)


def _has_non_blank_text(value: Any) -> bool:
    if type(value) is not str:
        return False
    try:
        stripped_value = value.strip()
        if type(stripped_value) is not str:
            return False
        return bool(stripped_value)
    except Exception:
        return False


def _normalize_request_method(method: Any) -> str:
    raw_method = method
    if isinstance(raw_method, bool):
        return "UNKNOWN"
    if isinstance(raw_method, Real):
        return "UNKNOWN"
    if isinstance(raw_method, (bytes, bytearray, memoryview)):
        try:
            raw_method = memoryview(raw_method).tobytes().decode("ascii")
        except (TypeError, ValueError, UnicodeDecodeError):
            return "UNKNOWN"
    elif not isinstance(raw_method, str):
        try:
            raw_method = str(raw_method)
        except Exception:
            return "UNKNOWN"
    try:
        if type(raw_method) is not str:
            return "UNKNOWN"
        stripped_method = raw_method.strip()
        if type(stripped_method) is not str or not stripped_method:
            return "UNKNOWN"
        normalized_method = stripped_method.upper()
        if type(normalized_method) is not str:
            return "UNKNOWN"
        lowered_method = normalized_method.lower()
        if type(lowered_method) is not str:
            return "UNKNOWN"
    except Exception:
        return "UNKNOWN"
    if (
        lowered_method in _INVALID_METHOD_SENTINELS
        or _NUMERIC_LIKE_METHOD_PATTERN.fullmatch(normalized_method)
    ):
        return "UNKNOWN"
    try:
        if len(normalized_method) > _MAX_REQUEST_METHOD_LENGTH:
            return "UNKNOWN"
        if not _HTTP_METHOD_TOKEN_PATTERN.fullmatch(normalized_method):
            return "UNKNOWN"
    except Exception:
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

    try:
        if type(raw_url) is not str:
            return "unknown URL"
        normalized_url = raw_url.strip()
        if type(normalized_url) is not str or not normalized_url:
            return "unknown URL"
        lowered_url = normalized_url.lower()
        if type(lowered_url) is not str:
            return "unknown URL"
    except Exception:
        return "unknown URL"
    if lowered_url in _INVALID_URL_SENTINELS or _NUMERIC_LIKE_URL_PATTERN.fullmatch(
        normalized_url
    ):
        return "unknown URL"
    try:
        if any(character.isspace() for character in normalized_url):
            return "unknown URL"
        if any(
            ord(character) < 32 or ord(character) == 127 for character in normalized_url
        ):
            return "unknown URL"
        if len(normalized_url) > _MAX_REQUEST_URL_DISPLAY_LENGTH:
            return f"{normalized_url[:_MAX_REQUEST_URL_DISPLAY_LENGTH]}... (truncated)"
    except Exception:
        return "unknown URL"
    return normalized_url


def _truncate_error_message(message: str) -> str:
    try:
        sanitized_message = _sanitize_error_message_text(message)
        if len(sanitized_message) <= _MAX_ERROR_MESSAGE_LENGTH:
            return sanitized_message
        return f"{sanitized_message[:_MAX_ERROR_MESSAGE_LENGTH]}... (truncated)"
    except Exception:
        return _safe_to_string(message)


def _normalize_response_text_for_error_message(response_text: Any) -> str:
    if type(response_text) is str:
        try:
            normalized_response_text = "".join(character for character in response_text)
            if type(normalized_response_text) is not str:
                raise TypeError("normalized response text must be a string")
            return normalized_response_text
        except Exception:
            return _safe_to_string(response_text)
    if isinstance(response_text, str):
        return _safe_to_string(response_text)
    if isinstance(response_text, (bytes, bytearray, memoryview)):
        try:
            return memoryview(response_text).tobytes().decode("utf-8")
        except (TypeError, ValueError, UnicodeDecodeError):
            return ""
    return _safe_to_string(response_text)


def _stringify_error_value(value: Any, *, _depth: int = 0) -> str:
    if _depth > 10:
        return _safe_to_string(value)
    if type(value) is str:
        try:
            normalized_value = "".join(character for character in value)
            if type(normalized_value) is not str:
                raise TypeError("normalized error value must be a string")
            return normalized_value
        except Exception:
            return _safe_to_string(value)
    if isinstance(value, str):
        return _safe_to_string(value)
    if isinstance(value, Mapping):
        for key in ("message", "error", "detail", "errors", "msg", "title", "reason"):
            try:
                nested_value = value.get(key)
            except Exception:
                continue
            if nested_value is not None:
                return _stringify_error_value(nested_value, _depth=_depth + 1)
    if isinstance(value, (list, tuple)):
        max_list_items = 10
        try:
            list_items = value[:max_list_items]
        except Exception:
            return _safe_to_string(value)
        collected_messages = []
        try:
            for item in list_items:
                item_message = _stringify_error_value(item, _depth=_depth + 1)
                if item_message:
                    collected_messages.append(item_message)
        except Exception:
            return _safe_to_string(value)
        if collected_messages:
            joined_messages = (
                collected_messages[0]
                if len(collected_messages) == 1
                else "; ".join(collected_messages)
            )
            try:
                remaining_items = len(value) - max_list_items
            except Exception:
                return joined_messages
            if remaining_items > 0:
                return f"{joined_messages}; ... (+{remaining_items} more)"
            return joined_messages
    try:
        return json.dumps(value, sort_keys=True)
    except (TypeError, ValueError, RecursionError):
        return _safe_to_string(value)


def extract_error_message(response: httpx.Response, fallback_error: Exception) -> str:
    def _fallback_message() -> str:
        try:
            response_text = _normalize_response_text_for_error_message(response.text)
        except Exception:
            response_text = ""
        if _has_non_blank_text(response_text):
            return _truncate_error_message(response_text)
        return _truncate_error_message(_safe_to_string(fallback_error))

    try:
        error_data: Any = response.json()
    except Exception:
        return _fallback_message()

    extracted_message: str
    if isinstance(error_data, Mapping):
        for key in ("message", "error", "detail", "errors", "title", "reason"):
            try:
                message = error_data.get(key)
            except Exception:
                continue
            if message is not None:
                candidate_message = _stringify_error_value(message)
                if _has_non_blank_text(candidate_message):
                    extracted_message = candidate_message
                    break
        else:
            extracted_message = _stringify_error_value(error_data)
    elif type(error_data) is str:
        extracted_message = error_data
    else:
        extracted_message = _stringify_error_value(error_data)

    if not _has_non_blank_text(extracted_message):
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
        request_url = request.url
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
