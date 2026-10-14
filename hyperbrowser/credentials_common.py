"""Credential fill serialization shared by sync and async clients."""

from typing import Any, Dict

from pydantic import ValidationError

from .client._request import coerce_request
from .exceptions import HyperbrowserError
from .models.credential import FillCredentialParams

CREDENTIAL_FILL_REQUEST_TIMEOUT_SECONDS = 30


def fill_credential_payload(params: Any) -> Dict[str, Any]:
    """Serialize aliases and frame targeting; the API validates fill policy."""
    try:
        request = coerce_request(params, FillCredentialParams)
    except ValidationError as error:
        problems = "; ".join(
            f"{'.'.join(str(part) for part in problem['loc']) or 'params'}: "
            f"{problem['msg']}"
            for problem in error.errors()
        )
        raise HyperbrowserError(
            f"Invalid credential fill request: {problems}", code="invalid_request"
        ) from None
    except TypeError as error:
        raise HyperbrowserError(str(error), code="invalid_request") from None

    body = request.model_dump(by_alias=True, exclude_none=True)
    if request.frame_url is not None:
        body["frame"] = {"url": request.frame_url}
    return body
