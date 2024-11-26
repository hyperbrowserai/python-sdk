import requests
from typing import Optional
from .base import TransportStrategy, APIResponse

class SyncTransport(TransportStrategy):
    """Synchronous transport implementation using requests"""
    def __init__(self, api_key: str):
        self.session = requests.Session()
        self.session.headers.update({"x-api-key": api_key})

    def close(self) -> None:
        self.session.close()

    def post(self, url: str) -> APIResponse:
        response = self.session.post(url)
        response.raise_for_status()
        try:
            return APIResponse(response.json()) if response.content else APIResponse.from_status(response.status_code)
        except requests.exceptions.JSONDecodeError:
            return APIResponse.from_status(response.status_code)

    def get(self, url: str, params: Optional[dict] = None) -> APIResponse:
        response = self.session.get(url, params=params)
        response.raise_for_status()
        try:
            return APIResponse(response.json()) if response.content else APIResponse.from_status(response.status_code)
        except requests.exceptions.JSONDecodeError:
            return APIResponse.from_status(response.status_code)

    def put(self, url: str) -> APIResponse:
        response = self.session.put(url)
        response.raise_for_status()
        try:
            return APIResponse(response.json()) if response.content else APIResponse.from_status(response.status_code)
        except requests.exceptions.JSONDecodeError:
            return APIResponse.from_status(response.status_code)