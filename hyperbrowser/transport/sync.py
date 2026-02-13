import json
import httpx
from typing import Mapping, Optional

from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.header_utils import merge_headers
from hyperbrowser.version import __version__
from .base import APIResponse, SyncTransportStrategy
from .error_utils import (
    extract_error_message,
    extract_request_error_context,
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
            except (httpx.DecodingError, json.JSONDecodeError, ValueError) as e:
                if response.status_code >= 400:
                    raise HyperbrowserError(
                        response.text or "Unknown error occurred",
                        status_code=response.status_code,
                        response=response,
                        original_error=e,
                    )
                return APIResponse.from_status(response.status_code)
        except httpx.HTTPStatusError as e:
            message = extract_error_message(response, fallback_error=e)
            raise HyperbrowserError(
                message,
                status_code=response.status_code,
                response=response,
                original_error=e,
            )
        except httpx.RequestError as e:
            request_method, request_url = extract_request_error_context(e)
            raise HyperbrowserError(
                f"Request {request_method} {request_url} failed", original_error=e
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
                f"Request POST {url} failed", original_error=e
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
                f"Request GET {url} failed", original_error=e
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
                f"Request PUT {url} failed", original_error=e
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
                f"Request DELETE {url} failed", original_error=e
            ) from e
