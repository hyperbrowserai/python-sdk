import json
from typing import Any

import httpx


def _stringify_error_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("message", "error", "detail"):
            nested_value = value.get(key)
            if nested_value is not None:
                return _stringify_error_value(nested_value)
    try:
        return json.dumps(value, sort_keys=True)
    except TypeError:
        return str(value)


def extract_error_message(response: httpx.Response, fallback_error: Exception) -> str:
    try:
        error_data: Any = response.json()
    except Exception:
        return response.text or str(fallback_error)

    if isinstance(error_data, dict):
        for key in ("message", "error", "detail"):
            message = error_data.get(key)
            if message is not None:
                return _stringify_error_value(message)
        return response.text or str(fallback_error)
    if isinstance(error_data, str):
        return error_data
    return _stringify_error_value(response.text or str(fallback_error))


def extract_request_error_context(error: httpx.RequestError) -> tuple[str, str]:
    try:
        request = error.request
    except RuntimeError:
        request = None
    if request is None:
        return "UNKNOWN", "unknown URL"
    return request.method, str(request.url)
