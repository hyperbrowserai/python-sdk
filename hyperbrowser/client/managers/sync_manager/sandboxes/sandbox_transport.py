import json
from typing import Dict, Iterator, Optional, Union

import httpx

from .....sandbox_common import (
    RuntimeConnection,
    build_headers,
    ensure_response_ok,
    normalize_network_error,
    parse_json_response,
    resolve_runtime_transport_target,
)
from ...sandboxes.shared import _build_query_path


class RuntimeTransport:
    def __init__(
        self,
        resolve_connection,
        timeout: float = 30.0,
        runtime_proxy_override: Optional[str] = None,
    ):
        self._resolve_connection = resolve_connection
        self._timeout = timeout
        self._runtime_proxy_override = runtime_proxy_override

    def request_json(
        self,
        path: str,
        *,
        method: str = "GET",
        params: Optional[Dict[str, object]] = None,
        json_body: Optional[Dict[str, object]] = None,
        content: Optional[Union[str, bytes]] = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        response = self._request(
            path,
            method=method,
            params=params,
            json_body=json_body,
            content=content,
            headers=headers,
        )
        return parse_json_response(response, "runtime")

    def request_bytes(
        self,
        path: str,
        *,
        method: str = "GET",
        params: Optional[Dict[str, object]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> bytes:
        response = self._request(path, method=method, params=params, headers=headers)
        return response.content

    def stream_sse(
        self, path: str, params: Optional[Dict[str, object]] = None
    ) -> Iterator[Dict[str, object]]:
        client, response = self._open_stream(path, params=params)
        event_name = "message"
        event_id = None
        data_lines = []

        def flush_event():
            nonlocal event_name, event_id, data_lines
            if not data_lines and event_name == "message" and event_id is None:
                return None

            raw_data = "\n".join(data_lines)
            data = raw_data
            if raw_data:
                try:
                    data = json.loads(raw_data)
                except json.JSONDecodeError:
                    data = raw_data

            event = {
                "event": event_name,
                "data": data,
                "id": event_id,
            }
            event_name = "message"
            event_id = None
            data_lines = []
            return event

        try:
            for line in response.iter_lines():
                if line == "":
                    event = flush_event()
                    if event is not None:
                        yield event
                    continue

                if line.startswith(":"):
                    continue

                if ":" in line:
                    field, value = line.split(":", 1)
                    value = value.lstrip(" ")
                else:
                    field, value = line, ""

                if field == "event":
                    event_name = value or "message"
                elif field == "data":
                    data_lines.append(value)
                elif field == "id":
                    event_id = value

            trailing = flush_event()
            if trailing is not None:
                yield trailing
        finally:
            response.close()
            client.close()

    def _request(
        self,
        path: str,
        *,
        method: str = "GET",
        params: Optional[Dict[str, object]] = None,
        json_body: Optional[Dict[str, object]] = None,
        content: Optional[Union[str, bytes]] = None,
        headers: Optional[Dict[str, str]] = None,
        allow_refresh: bool = True,
    ) -> httpx.Response:
        connection = self._resolve_connection(False)
        response = self._send(
            connection,
            path,
            method=method,
            params=params,
            json_body=json_body,
            content=content,
            headers=headers,
        )

        if response.status_code == 401 and allow_refresh:
            response.close()
            refreshed = self._resolve_connection(True)
            retry = self._send(
                refreshed,
                path,
                method=method,
                params=params,
                json_body=json_body,
                content=content,
                headers=headers,
            )
            return ensure_response_ok(retry, "runtime")

        return ensure_response_ok(response, "runtime")

    def _open_stream(
        self,
        path: str,
        *,
        params: Optional[Dict[str, object]] = None,
        allow_refresh: bool = True,
    ):
        connection = self._resolve_connection(False)
        client, response = self._send_stream(connection, path, params=params)
        if response.status_code == 401 and allow_refresh:
            response.close()
            client.close()
            refreshed = self._resolve_connection(True)
            client, response = self._send_stream(refreshed, path, params=params)

        if not response.is_success:
            response.read()
        ensure_response_ok(response, "runtime")
        return client, response

    def _send(
        self,
        connection: RuntimeConnection,
        path: str,
        *,
        method: str,
        params: Optional[Dict[str, object]],
        json_body: Optional[Dict[str, object]],
        content: Optional[Union[str, bytes]],
        headers: Optional[Dict[str, str]],
    ) -> httpx.Response:
        request_path = _build_query_path(path, params)
        target = resolve_runtime_transport_target(
            connection.base_url,
            request_path,
            self._runtime_proxy_override,
        )
        merged_headers = build_headers(connection.token, headers, target.host_header)
        client = httpx.Client(timeout=self._timeout)

        try:
            response = client.request(
                method,
                target.url,
                headers=merged_headers,
                json=json_body,
                content=content,
            )
        except BaseException as error:
            client.close()
            raise normalize_network_error(
                error,
                "runtime",
                "Unknown runtime request error",
            )

        response.read()
        client.close()
        return response

    def _send_stream(
        self,
        connection: RuntimeConnection,
        path: str,
        *,
        params: Optional[Dict[str, object]],
    ):
        request_path = _build_query_path(path, params)
        target = resolve_runtime_transport_target(
            connection.base_url,
            request_path,
            self._runtime_proxy_override,
        )
        headers = build_headers(
            connection.token,
            {"Accept": "text/event-stream"},
            target.host_header,
        )
        client = httpx.Client(timeout=self._timeout)

        try:
            request = client.build_request("GET", target.url, headers=headers)
            response = client.send(request, stream=True)
            return client, response
        except BaseException as error:
            client.close()
            raise normalize_network_error(
                error,
                "runtime",
                "Unknown runtime request error",
            )
