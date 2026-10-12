import json
import socket
import threading
import time
from typing import Any, Callable, Dict, Iterator, Optional

import httpx

from .....exceptions import HyperbrowserError
from .....sandbox_common import (
    RuntimeConnection,
    build_headers,
    ensure_response_ok,
    normalize_network_error,
    parse_json_response,
    request_context,
    resolve_runtime_transport_target,
)
from ...sandboxes.shared import (
    PROCESS_STREAM_IDLE_TIMEOUT_SECONDS,
    _build_query_path,
    _is_replayable_http_content,
)


class _DeadlineResponseStream(httpx.SyncByteStream):
    def __init__(self, stream, deadline):
        self._stream = stream
        self._deadline = deadline

    def __iter__(self):
        yield from self._stream

    def close(self) -> None:
        # Cancel before HTTPX releases the connection back to a shared pool.
        self._deadline.close()
        self._stream.close()


class _RequestDeadline:
    """Interrupt this request's socket when its total wait budget expires."""

    def __init__(self, deadline: float, shared_connection: bool = False):
        self.deadline = deadline
        self._shared_connection = shared_connection
        self._may_shutdown = True
        self._socket = None
        self._lock = threading.Lock()
        self._expired = False
        self._closed = False
        self._timer = threading.Timer(self.remaining(), self._expire)
        self._timer.daemon = True
        self._timer.start()

    def remaining(self) -> float:
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("Timed out waiting for command output")
        return remaining

    @staticmethod
    def _shutdown(sock) -> None:
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

    def _expire(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._expired = True
            sock = self._socket
        self._shutdown(sock)

    def trace(self, event, info) -> None:
        if "response_closed." in event or event.endswith(
            "receive_response_body.complete"
        ):
            # Response hooks may eagerly read/close before capture_response().
            # Cancel before the connection becomes available to another request,
            # and never interrupt the cleanup that releases it to the pool.
            self.close()
            return
        if self._shared_connection and event.startswith("http2."):
            with self._lock:
                self._may_shutdown = False
                self._socket = None
        # The HTTPX trace extension exposes the stream before response
        # headers, including the replacement stream after TLS negotiation.
        if event.endswith(("connect_tcp.complete", "start_tls.complete")):
            self.capture_stream(info.get("return_value"))
        self.remaining()

    def capture_stream(self, stream) -> None:
        if stream is not None:
            ssl_object = stream.get_extra_info("ssl_object")
            shared_http2 = (
                self._shared_connection
                and ssl_object is not None
                and ssl_object.selected_alpn_protocol() == "h2"
            )
            with self._lock:
                if self._closed:
                    return
                if shared_http2:
                    self._may_shutdown = False
                self._socket = (
                    stream.get_extra_info("socket") if self._may_shutdown else None
                )
                expired = self._expired
                sock = self._socket
            if expired:
                self._shutdown(sock)

    def capture_response(self, response: httpx.Response) -> None:
        if response.is_closed or response.is_stream_consumed:
            self.close()
            return
        self.capture_stream(response.extensions.get("network_stream"))
        response.stream = _DeadlineResponseStream(response.stream, self)

    def close(self) -> None:
        with self._lock:
            self._closed = True
        self._timer.cancel()
        self._timer.join()


class RuntimeTransport:
    def __init__(
        self,
        resolve_connection,
        timeout: float = 30.0,
        runtime_proxy_override: Optional[str] = None,
        resolve_connection_with_deadline: Optional[
            Callable[[bool, float], RuntimeConnection]
        ] = None,
    ):
        self._resolve_connection = resolve_connection
        self._timeout = timeout
        self._runtime_proxy_override = runtime_proxy_override
        self._resolve_connection_with_deadline = resolve_connection_with_deadline

    def _connection(self, force_refresh: bool, deadline: Optional[float]):
        if deadline is not None and self._resolve_connection_with_deadline is not None:
            return self._resolve_connection_with_deadline(force_refresh, deadline)
        return self._resolve_connection(force_refresh)

    def request_json(
        self,
        path: str,
        *,
        method: str = "GET",
        params: Optional[Dict[str, object]] = None,
        json_body: Optional[Dict[str, object]] = None,
        content: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
        request_timeout: Optional[float] = None,
        request_deadline: Optional[float] = None,
    ):
        response = self._request(
            path,
            method=method,
            params=params,
            json_body=json_body,
            content=content,
            headers=headers,
            request_timeout=request_timeout,
            request_deadline=request_deadline,
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

    def stream_bytes(
        self,
        path: str,
        *,
        method: str = "GET",
        params: Optional[Dict[str, object]] = None,
        headers: Optional[Dict[str, str]] = None,
        chunk_size: int = 65536,
    ) -> Iterator[bytes]:
        client, response = self._open_binary_stream(
            path,
            method=method,
            params=params,
            headers=headers,
        )
        try:
            for chunk in response.iter_bytes(chunk_size=chunk_size):
                if chunk:
                    yield chunk
        finally:
            response.close()
            client.close()

    def stream_sse(
        self,
        path: str,
        params: Optional[Dict[str, object]] = None,
        *,
        method: str = "GET",
        json_body: Optional[Dict[str, object]] = None,
        on_open: Optional[Callable] = None,
    ) -> Iterator[Dict[str, object]]:
        client, response = self._open_stream(
            path, params=params, method=method, json_body=json_body
        )
        if on_open is not None:

            def disconnect():
                # close() alone need not interrupt a recv() on another thread.
                # Each stream owns its HTTP client/connection, so shutdown is safe.
                network = response.extensions.get("network_stream")
                if network is not None:
                    sock = network.get_extra_info("socket")
                    if sock is not None:
                        try:
                            sock.shutdown(socket.SHUT_RDWR)
                        except OSError:
                            pass
                response.close()

            on_open(disconnect)
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
                # HTTPX < 0.24 includes line terminators in iter_lines().
                line = line.rstrip("\r\n")
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
        content: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
        allow_refresh: bool = True,
        request_timeout: Optional[float] = None,
        request_deadline: Optional[float] = None,
    ) -> httpx.Response:
        connection = self._connection(False, request_deadline)
        response = self._send(
            connection,
            path,
            method=method,
            params=params,
            json_body=json_body,
            content=content,
            headers=headers,
            request_timeout=request_timeout,
            request_deadline=request_deadline,
        )

        if response.status_code == 401 and allow_refresh:
            response.close()
            if not _is_replayable_http_content(content):
                return ensure_response_ok(
                    response,
                    "runtime",
                    "Runtime token expired during a streaming request; retry with a fresh stream.",
                )
            refreshed = self._connection(True, request_deadline)
            retry = self._send(
                refreshed,
                path,
                method=method,
                params=params,
                json_body=json_body,
                content=content,
                headers=headers,
                request_timeout=request_timeout,
                request_deadline=request_deadline,
            )
            return ensure_response_ok(retry, "runtime")

        return ensure_response_ok(response, "runtime")

    def _open_stream(
        self,
        path: str,
        *,
        params: Optional[Dict[str, object]] = None,
        allow_refresh: bool = True,
        method: str = "GET",
        json_body: Optional[Dict[str, object]] = None,
    ):
        connection = self._resolve_connection(False)
        client, response = self._send_stream(
            connection, path, params=params, method=method, json_body=json_body
        )
        if response.status_code == 401 and allow_refresh:
            response.close()
            client.close()
            refreshed = self._resolve_connection(True)
            client, response = self._send_stream(
                refreshed, path, params=params, method=method, json_body=json_body
            )

        try:
            if not response.is_success:
                response.read()
            ensure_response_ok(response, "runtime")
            if method == "POST" and "text/event-stream" not in response.headers.get(
                "content-type", ""
            ):
                raise HyperbrowserError(
                    "Receiver does not support streaming command start; update the receiver. The command may have started; do not retry it automatically.",
                    code="streaming_not_supported",
                    service="runtime",
                )
            if "text/event-stream" in response.headers.get("content-type", ""):
                # HTTPX passes this timeout extension through to body reads.
                # Change it before reading the body, after response headers have
                # arrived under the ordinary request timeout. Heartbeats reset
                # this idle timeout independently of the command's deadline.
                response.request.extensions["timeout"]["read"] = (
                    PROCESS_STREAM_IDLE_TIMEOUT_SECONDS
                )
        except BaseException:
            response.close()
            client.close()
            raise
        return client, response

    def _open_binary_stream(
        self,
        path: str,
        *,
        method: str = "GET",
        params: Optional[Dict[str, object]] = None,
        headers: Optional[Dict[str, str]] = None,
        allow_refresh: bool = True,
    ):
        connection = self._resolve_connection(False)
        client, response = self._send_binary_stream(
            connection,
            path,
            method=method,
            params=params,
            headers=headers,
        )
        if response.status_code == 401 and allow_refresh:
            response.close()
            client.close()
            refreshed = self._resolve_connection(True)
            client, response = self._send_binary_stream(
                refreshed,
                path,
                method=method,
                params=params,
                headers=headers,
            )

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
        content: Optional[Any],
        headers: Optional[Dict[str, str]],
        request_timeout: Optional[float] = None,
        request_deadline: Optional[float] = None,
    ) -> httpx.Response:
        request_path = _build_query_path(path, params)
        target = resolve_runtime_transport_target(
            connection.base_url,
            request_path,
            self._runtime_proxy_override,
        )
        merged_headers = build_headers(connection.token, headers, target.host_header)
        timeout = self._timeout if request_timeout is None else request_timeout
        deadline = None
        client = None
        try:
            if request_deadline is not None:
                deadline = _RequestDeadline(request_deadline)
                remaining = deadline.remaining()
                timeout = min(timeout, remaining) if timeout is not None else remaining
            client = httpx.Client(timeout=timeout)
            request_options: Dict[str, Any] = {}
            if deadline is not None:
                request_options["extensions"] = {"trace": deadline.trace}
            response = client.request(
                method,
                target.url,
                headers=merged_headers,
                json=json_body,
                content=content,
                **request_options,
            )
            if deadline is not None:
                deadline.remaining()
            response.read()
            return response
        except BaseException as error:
            raise normalize_network_error(
                error,
                "runtime",
                "Unknown runtime request error",
                request_context(method, path),
            )
        finally:
            if deadline is not None:
                deadline.close()
            if client is not None:
                client.close()

    def _send_binary_stream(
        self,
        connection: RuntimeConnection,
        path: str,
        *,
        method: str,
        params: Optional[Dict[str, object]],
        headers: Optional[Dict[str, str]],
    ):
        request_path = _build_query_path(path, params)
        target = resolve_runtime_transport_target(
            connection.base_url,
            request_path,
            self._runtime_proxy_override,
        )
        merged_headers = build_headers(connection.token, headers, target.host_header)
        client = httpx.Client(timeout=self._timeout)

        try:
            request = client.build_request(method, target.url, headers=merged_headers)
            response = client.send(request, stream=True)
            return client, response
        except BaseException as error:
            client.close()
            raise normalize_network_error(
                error,
                "runtime",
                "Unknown runtime request error",
                request_context(method, path),
            )

    def _send_stream(
        self,
        connection: RuntimeConnection,
        path: str,
        *,
        params: Optional[Dict[str, object]],
        method: str = "GET",
        json_body: Optional[Dict[str, object]] = None,
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
            request = client.build_request(
                method, target.url, headers=headers, json=json_body
            )
            response = client.send(request, stream=True)
            return client, response
        except BaseException as error:
            client.close()
            raise normalize_network_error(
                error,
                "runtime",
                "Unknown runtime request error",
                request_context(method, path),
            )
