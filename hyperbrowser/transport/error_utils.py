from typing import Any

import httpx


def extract_error_message(response: httpx.Response, fallback_error: Exception) -> str:
    try:
        error_data: Any = response.json()
    except Exception:
        return response.text or str(fallback_error)

    if isinstance(error_data, dict):
        message = error_data.get("message") or error_data.get("error")
        if message is not None:
            return str(message)
        return response.text or str(fallback_error)
    if isinstance(error_data, str):
        return error_data
    return str(response.text or str(fallback_error))
