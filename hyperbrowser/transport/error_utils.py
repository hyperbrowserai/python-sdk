from typing import Any

import httpx


def extract_error_message(response: httpx.Response, fallback_error: Exception) -> str:
    try:
        error_data: Any = response.json()
    except Exception:
        return response.text or str(fallback_error)

    if isinstance(error_data, dict):
        return (
            error_data.get("message")
            or error_data.get("error")
            or response.text
            or str(fallback_error)
        )
    if isinstance(error_data, str):
        return error_data
    return response.text or str(fallback_error)
