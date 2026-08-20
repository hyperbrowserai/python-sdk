import httpx
from typing import Any, Dict, Optional

from hyperbrowser.control_auth import coerce_transport_auth
from hyperbrowser.exceptions import HyperbrowserError
from .base import (
    TransportStrategy,
    APIResponse,
    is_request_replayable,
    retry_oauth_unauthorized,
)


class SyncTransport(TransportStrategy):
    """Synchronous transport implementation using httpx"""

    def __init__(self, auth):
        self.auth = coerce_transport_auth(auth)
        self.client = httpx.Client()

    def _handle_response(self, response: httpx.Response) -> APIResponse:
        try:
            response.raise_for_status()
            try:
                if not response.content:
                    return APIResponse.from_status(response.status_code)
                return APIResponse(response.json())
            except httpx.DecodingError as e:
                if response.status_code >= 400:
                    raise HyperbrowserError(
                        response.text or "Unknown error occurred",
                        status_code=response.status_code,
                        response=response,
                        original_error=e,
                    )
                return APIResponse.from_status(response.status_code)
        except httpx.HTTPStatusError as e:
            try:
                error_data = response.json()
                message = error_data.get("message") or error_data.get("error") or str(e)
            except Exception:
                message = str(e)
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
        self,
        url: str,
        data: Optional[dict] = None,
        files: Optional[dict] = None,
        timeout: Optional[float] = None,
    ) -> APIResponse:
        return self._request(
            "POST",
            url,
            json_data=None if files else data,
            data=data if files else None,
            files=files,
            timeout=timeout,
            replayable=is_request_replayable(files),
        )

    def get(
        self, url: str, params: Optional[dict] = None, follow_redirects: bool = False
    ) -> APIResponse:
        if params:
            params = {k: v for k, v in params.items() if v is not None}
        return self._request(
            "GET",
            url,
            params=params,
            follow_redirects=follow_redirects,
        )

    def put(self, url: str, data: Optional[dict] = None) -> APIResponse:
        return self._request("PUT", url, json_data=data)

    def delete(self, url: str) -> APIResponse:
        return self._request("DELETE", url)

    def send_authenticated(
        self,
        method: str,
        url: str,
        *,
        params: Optional[dict] = None,
        json: Optional[Any] = None,
        timeout: Optional[float] = None,
        follow_redirects: bool = False,
    ) -> httpx.Response:
        return self._exchange(
            method,
            url,
            params=params,
            json_data=json,
            timeout=timeout,
            follow_redirects=follow_redirects,
        )

    def _request(
        self,
        method: str,
        url: str,
        *,
        params: Optional[dict] = None,
        json_data: Optional[Any] = None,
        data: Optional[Any] = None,
        files: Optional[Any] = None,
        timeout: Optional[float] = None,
        follow_redirects: bool = False,
        replayable: bool = True,
    ) -> APIResponse:
        try:
            response = self._exchange(
                method,
                url,
                params=params,
                json_data=json_data,
                data=data,
                files=files,
                timeout=timeout,
                follow_redirects=follow_redirects,
                replayable=replayable,
            )
            return self._handle_response(response)
        except HyperbrowserError:
            raise
        except Exception as e:
            raise HyperbrowserError(
                f"{method.title()} request failed", original_error=e
            )

    def _exchange(
        self,
        method: str,
        url: str,
        *,
        params: Optional[dict] = None,
        json_data: Optional[Any] = None,
        data: Optional[Any] = None,
        files: Optional[Any] = None,
        timeout: Optional[float] = None,
        follow_redirects: bool = False,
        replayable: bool = True,
    ) -> httpx.Response:
        auth_headers, access_token = self.auth.authorize_headers()

        def send(headers: Dict[str, str]) -> httpx.Response:
            return self._send(
                method,
                url,
                params=params,
                json_data=json_data,
                data=data,
                files=files,
                auth_headers=headers,
                timeout=timeout,
                follow_redirects=follow_redirects,
            )

        return retry_oauth_unauthorized(
            self.auth,
            send(auth_headers),
            access_token=access_token,
            replayable=replayable,
            authorize=self.auth.authorize_headers,
            send=send,
            close_response=lambda response: response.close(),
        )

    def _send(
        self,
        method: str,
        url: str,
        *,
        params: Optional[dict],
        json_data: Optional[Any],
        data: Optional[Any],
        files: Optional[Any],
        auth_headers: Dict[str, str],
        timeout: Optional[float],
        follow_redirects: bool,
    ) -> httpx.Response:
        kwargs: Dict[str, Any] = {
            "headers": auth_headers,
            "follow_redirects": follow_redirects,
        }
        if params is not None:
            kwargs["params"] = params
        if timeout is not None:
            kwargs["timeout"] = timeout
        if json_data is not None:
            kwargs["json"] = json_data
        if data is not None:
            kwargs["data"] = data
        if files is not None:
            kwargs["files"] = files
        return self.client.request(method, url, **kwargs)
