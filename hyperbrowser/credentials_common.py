"""Credential fill rules shared by the sync and async clients and the tools."""

import re
from typing import Any, Dict

from pydantic import ValidationError

from .client._request import coerce_request
from .exceptions import HyperbrowserError
from .models.credential import FillCredentialParams

# Credential field names: the keys of a stored credential value, which are
# also the field names a fill writes.
CREDENTIAL_FIELD_PATTERN = re.compile(r"^[a-zA-Z0-9_.-]{1,64}$")
MAX_CREDENTIAL_FILL_FIELDS = 16
MAX_CREDENTIAL_SELECTOR_BYTES = 1024
MAX_CREDENTIAL_PAGE_ID_BYTES = 128
MAX_CREDENTIAL_FRAME_URL_BYTES = 2048
# The server gives a fill about 18 seconds, so wait longer than that.
CREDENTIAL_FILL_REQUEST_TIMEOUT_SECONDS = 30


def _invalid(message: str) -> HyperbrowserError:
    return HyperbrowserError(message, code="invalid_request")


def _utf8_length(value: str) -> int:
    return len(value.encode("utf-8", "surrogatepass"))


def fill_credential_payload(params: Any) -> Dict[str, Any]:
    """Check a fill request locally and return its JSON body.

    Raises ``HyperbrowserError`` with code ``invalid_request`` before any
    request is sent.
    """
    try:
        request = coerce_request(params, FillCredentialParams)
    except ValidationError as error:
        problems = "; ".join(
            f"{'.'.join(str(part) for part in problem['loc']) or 'params'}: "
            f"{problem['msg']}"
            for problem in error.errors()
        )
        raise _invalid(f"Invalid credential fill request: {problems}") from None
    except TypeError as error:
        raise _invalid(str(error)) from None

    if not request.credential.strip():
        raise _invalid("credential must name a credential attached to the session")
    if not 1 <= len(request.fields) <= MAX_CREDENTIAL_FILL_FIELDS:
        raise _invalid(
            f"fields must have 1 to {MAX_CREDENTIAL_FILL_FIELDS} entries, "
            f"got {len(request.fields)}"
        )
    seen = set()
    for entry in request.fields:
        if not CREDENTIAL_FIELD_PATTERN.fullmatch(entry.field):
            raise _invalid(
                f"Invalid field {entry.field!r}: field names are 1-64 letters, "
                "digits, '_', '.' or '-'"
            )
        if entry.field in seen:
            raise _invalid(f"Field {entry.field!r} is listed more than once")
        seen.add(entry.field)
        if not entry.selector.strip():
            raise _invalid(f"The selector for field {entry.field!r} is empty")
        if _utf8_length(entry.selector) > MAX_CREDENTIAL_SELECTOR_BYTES:
            raise _invalid(
                f"The selector for field {entry.field!r} is longer than "
                f"{MAX_CREDENTIAL_SELECTOR_BYTES} bytes"
            )
    if request.page_id is not None and not (
        0 < _utf8_length(request.page_id) <= MAX_CREDENTIAL_PAGE_ID_BYTES
    ):
        raise _invalid(
            f"page_id must be 1 to {MAX_CREDENTIAL_PAGE_ID_BYTES} bytes when set"
        )
    if request.frame is not None and not (
        0 < _utf8_length(request.frame.url) <= MAX_CREDENTIAL_FRAME_URL_BYTES
    ):
        raise _invalid(f"frame.url must be 1 to {MAX_CREDENTIAL_FRAME_URL_BYTES} bytes")
    return request.model_dump(by_alias=True, exclude_none=True)
