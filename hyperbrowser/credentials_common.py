"""Credential fill rules shared by the sync and async clients and the tools."""

from typing import Any, Dict

from pydantic import ValidationError

from .client._request import coerce_request
from .exceptions import HyperbrowserError
from .models.credential import FillCredentialParams
from .models.secret import SECRET_ENV_NAME_PATTERN, SECRET_NAME_PATTERN
from .models.vault import MAX_VAULT_ENV_NAME_LENGTH

MAX_CREDENTIAL_FILL_FIELDS = 16
MAX_CREDENTIAL_NAME_LENGTH = 255
MAX_CREDENTIAL_SELECTOR_BYTES = 1024
MAX_CREDENTIAL_PAGE_ID_BYTES = 128
MAX_CREDENTIAL_URL_BYTES = 2048
# The server gives a fill about 18 seconds, so wait longer than that.
CREDENTIAL_FILL_REQUEST_TIMEOUT_SECONDS = 30


def _invalid(message: str) -> HyperbrowserError:
    return HyperbrowserError(message, code="invalid_request")


def _utf8_length(value: str) -> int:
    return len(value.encode("utf-8", "surrogatepass"))


def _check_bytes(value: Any, name: str, limit: int) -> None:
    if value is not None and not 0 < _utf8_length(value) <= limit:
        raise _invalid(f"{name} must be 1 to {limit} bytes when set")


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

    if (request.credential is None) == (request.vault is None):
        raise _invalid(
            "Pass exactly one of credential (a secret attached to the session) "
            "and vault (a vault attached to the session)"
        )
    if request.credential is not None and not (
        request.credential.strip()
        and len(request.credential) <= MAX_CREDENTIAL_NAME_LENGTH
    ):
        raise _invalid("credential must name a secret attached to the session")
    if request.vault is not None and not SECRET_NAME_PATTERN.fullmatch(request.vault):
        raise _invalid(
            f"Invalid vault name {request.vault!r}: names are 1-128 letters, "
            "digits, '_' or '-', starting with a letter or digit"
        )
    if not 1 <= len(request.fields) <= MAX_CREDENTIAL_FILL_FIELDS:
        raise _invalid(
            f"fields must have 1 to {MAX_CREDENTIAL_FILL_FIELDS} entries, "
            f"got {len(request.fields)}"
        )
    selectors = set()
    for entry in request.fields:
        if not entry.selector.strip():
            raise _invalid("A field's selector is empty")
        if _utf8_length(entry.selector) > MAX_CREDENTIAL_SELECTOR_BYTES:
            raise _invalid(
                f"The selector {entry.selector[:64]!r} is longer than "
                f"{MAX_CREDENTIAL_SELECTOR_BYTES} bytes"
            )
        if entry.selector in selectors:
            raise _invalid(f"The selector {entry.selector!r} is listed more than once")
        selectors.add(entry.selector)
        if request.vault is None:
            if entry.field is not None:
                raise _invalid(
                    "field names a vault entry; leave it out when filling a "
                    "single credential"
                )
        elif entry.field is None:
            raise _invalid(
                f"The field for {entry.selector!r} needs field: the vault entry "
                "to type"
            )
        elif (
            not SECRET_ENV_NAME_PATTERN.fullmatch(entry.field)
            or len(entry.field) > MAX_VAULT_ENV_NAME_LENGTH
            or entry.field == "__proto__"
        ):
            raise _invalid(
                f"Invalid field {entry.field!r}: vault entries are environment "
                "variable names (letters, digits and '_', not starting with a digit)"
            )
    if request.page_id is not None and request.page_url is not None:
        raise _invalid("Pass page_id or page_url, not both")
    _check_bytes(request.page_id, "page_id", MAX_CREDENTIAL_PAGE_ID_BYTES)
    _check_bytes(request.page_url, "page_url", MAX_CREDENTIAL_URL_BYTES)
    _check_bytes(request.frame_url, "frame_url", MAX_CREDENTIAL_URL_BYTES)

    body = request.model_dump(by_alias=True, exclude_none=True)
    if request.frame_url is not None:
        body["frame"] = {"url": request.frame_url}
    return body
