_TRUNCATED_DISPLAY_SUFFIX = "... (truncated)"


def normalize_display_text(value: str, *, max_length: int) -> str:
    try:
        sanitized_value = "".join(
            "?" if ord(character) < 32 or ord(character) == 127 else character
            for character in value
        ).strip()
        if type(sanitized_value) is not str:
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
