import json
import httpx
from typing import Mapping, Optional

from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.header_utils import merge_headers
from hyperbrowser.version import __version__
from .base import APIResponse, AsyncTransportStrategy
from .error_utils import (
    extract_error_message,
    extract_request_error_context,
    format_request_failure_message,
)


class AsyncTransport(AsyncTransportStrategy):
    """Asynchronous transport implementation using httpx"""

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
        self.client = httpx.AsyncClient(headers=merged_headers)
        self._closed = False

    async def close(self) -> None:
        if not self._closed:
            await self.client.aclose()
            self._closed = True

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def _handle_response(self, response: httpx.Response) -> APIResponse:
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

    async def post(
        self, url: str, data: Optional[dict] = None, files: Optional[dict] = None
    ) -> APIResponse:
        try:
            if files:
                response = await self.client.post(url, data=data, files=files)
            else:
                response = await self.client.post(url, json=data)
            return await self._handle_response(response)
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

    async def get(
        self, url: str, params: Optional[dict] = None, follow_redirects: bool = False
    ) -> APIResponse:
        if params:
            params = {k: v for k, v in params.items() if v is not None}
        try:
            response = await self.client.get(
                url, params=params, follow_redirects=follow_redirects
            )
            return await self._handle_response(response)
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

    async def put(self, url: str, data: Optional[dict] = None) -> APIResponse:
        try:
            response = await self.client.put(url, json=data)
            return await self._handle_response(response)
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

    async def delete(self, url: str) -> APIResponse:
        try:
            response = await self.client.delete(url)
            return await self._handle_response(response)
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
