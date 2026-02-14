from hyperbrowser.type_utils import is_plain_int, is_plain_string

_TRUNCATED_DISPLAY_SUFFIX = "... (truncated)"
_DEFAULT_BLANK_KEY_FALLBACK = "<blank key>"
_DEFAULT_MAX_DISPLAY_LENGTH = 200


def normalize_display_text(value: object, *, max_length: object) -> str:
    if not is_plain_string(value):
        return ""
    if not is_plain_int(max_length) or max_length <= 0:
        max_length = _DEFAULT_MAX_DISPLAY_LENGTH
    try:
        sanitized_value = "".join(
            "?" if ord(character) < 32 or ord(character) == 127 else character
            for character in value
        ).strip()
        if not is_plain_string(sanitized_value):
            return ""
        if not sanitized_value:
            return ""
        if len(sanitized_value) <= max_length:
            return sanitized_value
        available_length = max_length - len(_TRUNCATED_DISPLAY_SUFFIX)
        if available_length <= 0:
            return _TRUNCATED_DISPLAY_SUFFIX
        return f"{sanitized_value[:available_length]}{_TRUNCATED_DISPLAY_SUFFIX}"
    except Exception:
        return ""


def _normalize_blank_key_fallback(*, fallback: object, max_length: object) -> str:
    normalized_fallback = normalize_display_text(fallback, max_length=max_length)
    if normalized_fallback:
        return normalized_fallback
    return _DEFAULT_BLANK_KEY_FALLBACK


def format_string_key_for_error(
    key: object,
    *,
    max_length: object,
    blank_fallback: object = _DEFAULT_BLANK_KEY_FALLBACK,
) -> str:
    normalized_key = normalize_display_text(key, max_length=max_length)
    if not normalized_key:
        return _normalize_blank_key_fallback(
            fallback=blank_fallback,
            max_length=max_length,
        )
    return normalized_key
