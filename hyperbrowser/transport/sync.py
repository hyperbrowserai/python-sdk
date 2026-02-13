import json
import httpx
from typing import Mapping, Optional

from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.version import __version__
from .base import APIResponse, SyncTransportStrategy
from .error_utils import extract_error_message


class SyncTransport(SyncTransportStrategy):
    """Synchronous transport implementation using httpx"""

    def __init__(self, api_key: str, headers: Optional[Mapping[str, str]] = None):
        merged_headers = {
            "x-api-key": api_key,
            "User-Agent": f"hyperbrowser-python-sdk/{__version__}",
        }
        if headers:
            normalized_headers = {}
            for key, value in headers.items():
                if not isinstance(key, str) or not isinstance(value, str):
                    raise HyperbrowserError("headers must be a mapping of string pairs")
                normalized_key = key.strip()
                if not normalized_key:
                    raise HyperbrowserError("header names must not be empty")
                if (
                    "\n" in normalized_key
                    or "\r" in normalized_key
                    or "\n" in value
                    or "\r" in value
                ):
                    raise HyperbrowserError(
                        "headers must not contain newline characters"
                    )
                normalized_headers[normalized_key] = value
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
