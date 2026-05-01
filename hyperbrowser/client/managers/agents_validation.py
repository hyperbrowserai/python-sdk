from typing import Mapping, Optional
from urllib.parse import urlparse

from hyperbrowser.exceptions import HyperbrowserError


def _is_absolute_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def validate_custom_api_keys(
    use_custom_api_keys: Optional[bool],
    api_keys: Optional[object],
    base_urls: Mapping[str, Optional[str]],
) -> None:
    if use_custom_api_keys and api_keys is None:
        raise HyperbrowserError("api_keys must be provided when use_custom_api_keys is true")

    for field, value in base_urls.items():
        if value is not None and not _is_absolute_http_url(value):
            raise HyperbrowserError(f"{field} must be an absolute http or https URL")
