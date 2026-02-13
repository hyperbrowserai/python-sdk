import json
import httpx
from typing import Mapping, Optional

from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.header_utils import normalize_headers
from hyperbrowser.version import __version__
from .base import APIResponse, SyncTransportStrategy
from .error_utils import extract_error_message


class SyncTransport(SyncTransportStrategy):
    """Synchronous transport implementation using httpx"""

    def __init__(self, api_key: str, headers: Optional[Mapping[str, str]] = None):
        if not isinstance(api_key, str):
            raise HyperbrowserError("api_key must be a string")
        normalized_api_key = api_key.strip()
        if not normalized_api_key:
            raise HyperbrowserError("api_key must not be empty")
        merged_headers = {
            "x-api-key": normalized_api_key,
            "User-Agent": f"hyperbrowser-python-sdk/{__version__}",
        }
        normalized_headers = normalize_headers(
            headers,
            mapping_error_message="headers must be a mapping of string pairs",
        )
        if normalized_headers:
            merged_headers.update(normalized_headers)
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
            raise HyperbrowserError("Request failed", original_error=e)

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
        except HyperbrowserError:
            raise
        except Exception as e:
            raise HyperbrowserError("Post request failed", original_error=e)

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
        except HyperbrowserError:
            raise
        except Exception as e:
            raise HyperbrowserError("Get request failed", original_error=e)

    def put(self, url: str, data: Optional[dict] = None) -> APIResponse:
        try:
            response = self.client.put(url, json=data)
            return self._handle_response(response)
        except HyperbrowserError:
            raise
        except Exception as e:
            raise HyperbrowserError("Put request failed", original_error=e)

    def delete(self, url: str) -> APIResponse:
        try:
            response = self.client.delete(url)
            return self._handle_response(response)
        except HyperbrowserError:
            raise
        except Exception as e:
            raise HyperbrowserError("Delete request failed", original_error=e)
