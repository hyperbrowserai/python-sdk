import json
from typing import Any

import httpx


def _stringify_error_value(value: Any, *, _depth: int = 0) -> str:
    if _depth > 10:
        return str(value)
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("message", "error", "detail", "errors", "msg"):
            nested_value = value.get(key)
            if nested_value is not None:
                return _stringify_error_value(nested_value, _depth=_depth + 1)
    if isinstance(value, (list, tuple)):
        collected_messages = [
            item_message
            for item_message in (
                _stringify_error_value(item, _depth=_depth + 1) for item in value
            )
            if item_message
        ]
        if collected_messages:
            return (
                collected_messages[0]
                if len(collected_messages) == 1
                else "; ".join(collected_messages)
            )
    try:
        return json.dumps(value, sort_keys=True)
    except (TypeError, ValueError, RecursionError):
        return str(value)


def extract_error_message(response: httpx.Response, fallback_error: Exception) -> str:
    def _fallback_message() -> str:
        return response.text or str(fallback_error)

    try:
        error_data: Any = response.json()
    except Exception:
        return _fallback_message()

    extracted_message: str
    if isinstance(error_data, dict):
        for key in ("message", "error", "detail", "errors"):
            message = error_data.get(key)
            if message is not None:
                extracted_message = _stringify_error_value(message)
                break
        else:
            extracted_message = _stringify_error_value(error_data)
    elif isinstance(error_data, str):
        extracted_message = error_data
    else:
        extracted_message = _stringify_error_value(error_data)

    return extracted_message if extracted_message.strip() else _fallback_message()


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
    if not isinstance(request_method, str) or not request_method.strip():
        request_method = "UNKNOWN"

    try:
        request_url = str(request.url)
    except Exception:
        request_url = "unknown URL"
    if not request_url.strip():
        request_url = "unknown URL"
    return request_method, request_url


def format_request_failure_message(
    error: httpx.RequestError, *, fallback_method: str, fallback_url: str
) -> str:
    request_method, request_url = extract_request_error_context(error)
    effective_method = (
        request_method if request_method != "UNKNOWN" else fallback_method
    )
    if not isinstance(effective_method, str) or not effective_method.strip():
        effective_method = "UNKNOWN"

    effective_url = request_url if request_url != "unknown URL" else fallback_url
    if not isinstance(effective_url, str) or not effective_url.strip():
        effective_url = "unknown URL"
    return f"Request {effective_method} {effective_url} failed"
