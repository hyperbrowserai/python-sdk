import httpx
from typing import Mapping, Optional

from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.header_utils import merge_headers
from hyperbrowser.version import __version__
from .base import APIResponse, SyncTransportStrategy
from .error_utils import (
    extract_error_message,
    format_generic_request_failure_message,
    format_request_failure_message,
)


class SyncTransport(SyncTransportStrategy):
    """Synchronous transport implementation using httpx"""

    def __init__(self, api_key: str, headers: Optional[Mapping[str, str]] = None):
        if not isinstance(api_key, str):
            raise HyperbrowserError("api_key must be a string")
        normalized_api_key = api_key.strip()
        if not normalized_api_key:
            raise HyperbrowserError("api_key must not be empty")
        if any(
            ord(character) < 32 or ord(character) == 127
            for character in normalized_api_key
        ):
            raise HyperbrowserError("api_key must not contain control characters")
        merged_headers = merge_headers(
            {
                "x-api-key": normalized_api_key,
                "User-Agent": f"hyperbrowser-python-sdk/{__version__}",
            },
            headers,
            mapping_error_message="headers must be a mapping of string pairs",
        )
        self.client = httpx.Client(headers=merged_headers)

    def _handle_response(self, response: httpx.Response) -> APIResponse:
        try:
            response.raise_for_status()
            try:
                if not response.content:
                    return APIResponse.from_status(response.status_code)
                return APIResponse(response.json())
            except Exception as e:
                try:
                    status_code = response.status_code
                    if isinstance(status_code, bool):
                        raise TypeError("boolean status code is invalid")
                    normalized_status_code = int(status_code)
                except Exception as status_exc:
                    raise HyperbrowserError(
                        "Failed to process response status code",
                        original_error=status_exc,
                    ) from status_exc
                if normalized_status_code >= 400:
                    try:
                        response_text = response.text
                    except Exception:
                        response_text = ""
                    raise HyperbrowserError(
                        response_text or "Unknown error occurred",
                        status_code=normalized_status_code,
                        response=response,
                        original_error=e,
                    )
                return APIResponse.from_status(normalized_status_code)
        except httpx.HTTPStatusError as e:
            message = extract_error_message(response, fallback_error=e)
            raise HyperbrowserError(
                message,
                status_code=response.status_code,
                response=response,
                original_error=e,
            )
        except httpx.RequestError as e:
            raise HyperbrowserError(
                format_request_failure_message(
                    e,
                    fallback_method="UNKNOWN",
                    fallback_url="unknown URL",
                ),
                original_error=e,
            )

    def close(self) -> None:
        self.client.close()

    def post(
        self, url: str, data: Optional[dict] = None, files: Optional[dict] = None
    ) -> APIResponse:
        try:
            if files:
                response = self.client.post(url, data=data, files=files)
            else:
                response = self.client.post(url, json=data)
            return self._handle_response(response)
        except httpx.RequestError as e:
            raise HyperbrowserError(
                format_request_failure_message(
                    e, fallback_method="POST", fallback_url=url
                ),
                original_error=e,
            ) from e
        except HyperbrowserError:
            raise
        except Exception as e:
            raise HyperbrowserError(
                format_generic_request_failure_message(method="POST", url=url),
                original_error=e,
            ) from e

    def get(
        self, url: str, params: Optional[dict] = None, follow_redirects: bool = False
    ) -> APIResponse:
        if params:
            params = {k: v for k, v in params.items() if v is not None}
        try:
            response = self.client.get(
                url, params=params, follow_redirects=follow_redirects
            )
            return self._handle_response(response)
        except httpx.RequestError as e:
            raise HyperbrowserError(
                format_request_failure_message(
                    e, fallback_method="GET", fallback_url=url
                ),
                original_error=e,
            ) from e
        except HyperbrowserError:
            raise
        except Exception as e:
            raise HyperbrowserError(
                format_generic_request_failure_message(method="GET", url=url),
                original_error=e,
            ) from e

    def put(self, url: str, data: Optional[dict] = None) -> APIResponse:
        try:
            response = self.client.put(url, json=data)
            return self._handle_response(response)
        except httpx.RequestError as e:
            raise HyperbrowserError(
                format_request_failure_message(
                    e, fallback_method="PUT", fallback_url=url
                ),
                original_error=e,
            ) from e
        except HyperbrowserError:
            raise
        except Exception as e:
            raise HyperbrowserError(
                format_generic_request_failure_message(method="PUT", url=url),
                original_error=e,
            ) from e

    def delete(self, url: str) -> APIResponse:
        try:
            response = self.client.delete(url)
            return self._handle_response(response)
        except httpx.RequestError as e:
            raise HyperbrowserError(
                format_request_failure_message(
                    e, fallback_method="DELETE", fallback_url=url
                ),
                original_error=e,
            ) from e
        except HyperbrowserError:
            raise
        except Exception as e:
            raise HyperbrowserError(
                format_generic_request_failure_message(method="DELETE", url=url),
                original_error=e,
            ) from e
