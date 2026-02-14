from hyperbrowser.type_utils import is_plain_string

_TRUNCATED_DISPLAY_SUFFIX = "... (truncated)"


def normalize_display_text(value: str, *, max_length: int) -> str:
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


def format_string_key_for_error(
    key: str,
    *,
    max_length: int,
    blank_fallback: str = "<blank key>",
) -> str:
    normalized_key = normalize_display_text(key, max_length=max_length)
    if not normalized_key:
        return blank_fallback
    return normalized_key
