import json
from typing import Dict, Mapping, Optional, cast

from .exceptions import HyperbrowserError


def normalize_headers(
    headers: Optional[Mapping[str, str]],
    *,
    mapping_error_message: str,
    pair_error_message: Optional[str] = None,
) -> Optional[Dict[str, str]]:
    if headers is None:
        return None
    if not isinstance(headers, Mapping):
        raise HyperbrowserError(mapping_error_message)

    effective_pair_error_message = pair_error_message or mapping_error_message
    normalized_headers: Dict[str, str] = {}
    for key, value in headers.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise HyperbrowserError(effective_pair_error_message)
        normalized_key = key.strip()
        if not normalized_key:
            raise HyperbrowserError("header names must not be empty")
        if (
            "\n" in normalized_key
            or "\r" in normalized_key
            or "\n" in value
            or "\r" in value
        ):
            raise HyperbrowserError("headers must not contain newline characters")
        if normalized_key in normalized_headers:
            raise HyperbrowserError(
                "duplicate header names are not allowed after normalization"
            )
        normalized_headers[normalized_key] = value
    return normalized_headers


def parse_headers_env_json(raw_headers: Optional[str]) -> Optional[Dict[str, str]]:
    if raw_headers is None:
        return None
    if not isinstance(raw_headers, str):
        raise HyperbrowserError("HYPERBROWSER_HEADERS must be a string")
    if not raw_headers.strip():
        return None
    try:
        parsed_headers = json.loads(raw_headers)
    except json.JSONDecodeError as exc:
        raise HyperbrowserError(
            "HYPERBROWSER_HEADERS must be valid JSON object"
        ) from exc
    if not isinstance(parsed_headers, Mapping):
        raise HyperbrowserError(
            "HYPERBROWSER_HEADERS must be a JSON object of string pairs"
        )
    return normalize_headers(
        cast(Mapping[str, str], parsed_headers),
        mapping_error_message="HYPERBROWSER_HEADERS must be a JSON object of string pairs",
        pair_error_message="HYPERBROWSER_HEADERS must be a JSON object of string pairs",
    )
