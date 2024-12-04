import requests
from typing import Optional

from hyperbrowser.exceptions import HyperbrowserError
from .base import TransportStrategy, APIResponse


class SyncTransport(TransportStrategy):
    """Synchronous transport implementation using requests"""

    def __init__(self, api_key: str):
        self.session = requests.Session()
        self.session.headers.update({"x-api-key": api_key})

    def _handle_response(self, response: requests.Response) -> APIResponse:
        try:
            response.raise_for_status()
            try:
                if not response.content:
                    return APIResponse.from_status(response.status_code)
                return APIResponse(response.json())
            except requests.exceptions.JSONDecodeError as e:
                if response.status_code >= 400:
                    raise HyperbrowserError(
                        response.text or "Unknown error occurred",
                        status_code=response.status_code,
                        response=response,
                        original_error=e,
                    )
                return APIResponse.from_status(response.status_code)
        except requests.exceptions.HTTPError as e:
            try:
                error_data = response.json()
                message = error_data.get("message") or error_data.get("error") or str(e)
            except:
                message = str(e)
            raise HyperbrowserError(
                message,
                status_code=response.status_code,
                response=response,
                original_error=e,
            )
        except requests.RequestException as e:
            raise HyperbrowserError("Request failed", original_error=e)

    def close(self) -> None:
        self.session.close()

    def post(self, url: str) -> APIResponse:
        try:
            response = self.session.post(url)
            return self._handle_response(response)
        except HyperbrowserError:
            raise
        except Exception as e:
            raise HyperbrowserError("Post request failed", original_error=e)

    def get(self, url: str, params: Optional[dict] = None) -> APIResponse:
        if params:
            params = {k: v for k, v in params.items() if v is not None}
        try:
            response = self.session.get(url, params=params)
            return self._handle_response(response)
        except HyperbrowserError:
            raise
        except Exception as e:
            raise HyperbrowserError("Get request failed", original_error=e)

    def put(self, url: str) -> APIResponse:
        try:
            response = self.session.put(url)
            return self._handle_response(response)
        except HyperbrowserError:
            raise
        except Exception as e:
            raise HyperbrowserError("Put request failed", original_error=e)
