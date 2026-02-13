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
    seen_header_names = set()
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
        if any(
            ord(character) < 32 or ord(character) == 127
            for character in f"{normalized_key}{value}"
        ):
            raise HyperbrowserError("headers must not contain control characters")
        canonical_header_name = normalized_key.lower()
        if canonical_header_name in seen_header_names:
            raise HyperbrowserError(
                "duplicate header names are not allowed after normalization"
            )
        seen_header_names.add(canonical_header_name)
        normalized_headers[normalized_key] = value
    return normalized_headers


def merge_headers(
    base_headers: Mapping[str, str],
    override_headers: Optional[Mapping[str, str]],
    *,
    mapping_error_message: str,
    pair_error_message: Optional[str] = None,
) -> Dict[str, str]:
    normalized_base_headers = normalize_headers(
        base_headers,
        mapping_error_message=mapping_error_message,
        pair_error_message=pair_error_message,
    )
    merged_headers = dict(normalized_base_headers or {})
    normalized_overrides = normalize_headers(
        override_headers,
        mapping_error_message=mapping_error_message,
        pair_error_message=pair_error_message,
    )
    if not normalized_overrides:
        return merged_headers

    existing_canonical_to_key = {key.lower(): key for key in merged_headers}
    for override_key, override_value in normalized_overrides.items():
        canonical_override_key = override_key.lower()
        existing_key = existing_canonical_to_key.get(canonical_override_key)
        if existing_key is not None:
            del merged_headers[existing_key]
        merged_headers[override_key] = override_value
        existing_canonical_to_key[canonical_override_key] = override_key
    return merged_headers


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
