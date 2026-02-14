import json
import re
from typing import Dict, Mapping, Optional, cast

from .exceptions import HyperbrowserError

_INVALID_HEADER_NAME_CHARACTER_PATTERN = re.compile(r"[^!#$%&'*+\-.^_`|~0-9A-Za-z]")
_MAX_HEADER_NAME_LENGTH = 256


def _read_header_items(
    headers: Mapping[str, str], *, mapping_error_message: str
) -> list[tuple[object, object]]:
    try:
        raw_items = list(headers.items())
    except HyperbrowserError:
        raise
    except Exception as exc:
        raise HyperbrowserError(mapping_error_message, original_error=exc) from exc
    normalized_items: list[tuple[object, object]] = []
    for item in raw_items:
        try:
            if not isinstance(item, tuple):
                raise HyperbrowserError(mapping_error_message)
            if len(item) != 2:
                raise HyperbrowserError(mapping_error_message)
            normalized_items.append((item[0], item[1]))
        except HyperbrowserError:
            raise
        except Exception as exc:
            raise HyperbrowserError(mapping_error_message, original_error=exc) from exc
    return normalized_items


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
    for key, value in _read_header_items(
        headers, mapping_error_message=mapping_error_message
    ):
        if not isinstance(key, str) or not isinstance(value, str):
            raise HyperbrowserError(effective_pair_error_message)
        try:
            normalized_key = key.strip()
            if not isinstance(normalized_key, str):
                raise TypeError("normalized header name must be a string")
        except HyperbrowserError:
            raise
        except Exception as exc:
            raise HyperbrowserError(
                "Failed to normalize header name",
                original_error=exc,
            ) from exc
        if not normalized_key:
            raise HyperbrowserError("header names must not be empty")
        if len(normalized_key) > _MAX_HEADER_NAME_LENGTH:
            raise HyperbrowserError(
                f"header names must be {_MAX_HEADER_NAME_LENGTH} characters or fewer"
            )
        if _INVALID_HEADER_NAME_CHARACTER_PATTERN.search(normalized_key):
            raise HyperbrowserError(
                "header names must contain only valid HTTP token characters"
            )
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
        try:
            canonical_header_name = normalized_key.lower()
            if not isinstance(canonical_header_name, str):
                raise TypeError("canonical header name must be a string")
        except HyperbrowserError:
            raise
        except Exception as exc:
            raise HyperbrowserError(
                "Failed to normalize header name",
                original_error=exc,
            ) from exc
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
    except HyperbrowserError:
        raise
    except Exception as exc:
        raise HyperbrowserError(
            "HYPERBROWSER_HEADERS must be valid JSON object",
            original_error=exc,
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
