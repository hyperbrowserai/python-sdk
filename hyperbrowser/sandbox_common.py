import json
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpx

from .exceptions import HyperbrowserError, HyperbrowserService

RETRYABLE_STATUS_CODES = {429, 502, 503, 504}
RUNTIME_SESSION_REFRESH_BUFFER_MS = 60_000


@dataclass(frozen=True)
class RuntimeConnection:
    sandbox_id: str
    base_url: str
    token: str


@dataclass(frozen=True)
class RuntimeTransportTarget:
    url: str
    host_header: Optional[str] = None
    connect_host: Optional[str] = None
    connect_port: Optional[int] = None


def get_request_id(response: httpx.Response) -> Optional[str]:
    return response.headers.get("x-request-id") or response.headers.get("request-id")


def is_retryable_network_error(error: BaseException) -> bool:
    return isinstance(
        error,
        (
            httpx.TimeoutException,
            httpx.NetworkError,
            httpx.RemoteProtocolError,
            httpx.ProxyError,
            httpx.ReadError,
            httpx.WriteError,
            httpx.PoolTimeout,
        ),
    )


def parse_error_payload(
    raw_text: str, fallback_message: str
) -> Tuple[str, Optional[str], Any]:
    if not raw_text:
        return fallback_message, None, None

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        return raw_text, None, raw_text

    if isinstance(parsed, dict):
        message = parsed.get("message") or parsed.get("error") or fallback_message
        code = parsed.get("code") if isinstance(parsed.get("code"), str) else None
        return message, code, parsed

    return fallback_message, None, parsed


def ensure_response_ok(
    response: httpx.Response,
    service: HyperbrowserService,
    default_message: Optional[str] = None,
) -> httpx.Response:
    if response.is_success:
        return response

    fallback = default_message or (
        f"Request failed: {response.status_code} {response.reason_phrase}"
    )
    message, code, details = parse_error_payload(response.text, fallback)
    raise HyperbrowserError(
        message,
        status_code=response.status_code,
        response=response,
        code=code,
        request_id=get_request_id(response),
        retryable=response.status_code in RETRYABLE_STATUS_CODES,
        service=service,
        details=details,
    )


def parse_json_response(
    response: httpx.Response,
    service: HyperbrowserService,
    default_message: str = "Failed to parse JSON response",
) -> Any:
    if not response.content:
        return {}

    try:
        return response.json()
    except json.JSONDecodeError as error:
        raise HyperbrowserError(
            default_message,
            status_code=response.status_code,
            response=response,
            request_id=get_request_id(response),
            retryable=False,
            service=service,
            cause=error,
        )


def has_scheme(value: str) -> bool:
    return "://" in value


def runtime_base_url_session_id(runtime_base_url: str) -> Optional[str]:
    parsed_base_url = urlsplit(runtime_base_url.strip())
    segments = [
        segment
        for segment in parsed_base_url.path.strip().strip("/").split("/")
        if segment
    ]
    if len(segments) < 2 or segments[0] != "sandbox" or not segments[1].strip():
        return None
    return segments[1].strip()


def should_prepend_sandbox_to_runtime_api(runtime_base_url: str) -> bool:
    return runtime_base_url_session_id(runtime_base_url) is None


def normalize_runtime_api_path(pathname: str, prepend_sandbox: bool) -> str:
    trimmed = pathname.strip()
    if trimmed == "":
        return "/sandbox" if prepend_sandbox else "/"

    absolute = trimmed if trimmed.startswith("/") else f"/{trimmed}"
    if prepend_sandbox:
        if absolute == "/sandbox" or absolute.startswith("/sandbox/"):
            return absolute
        return f"/sandbox{absolute}"

    if absolute == "/sandbox":
        return "/"
    if absolute.startswith("/sandbox/"):
        return f"/{absolute[len('/sandbox/'):]}"
    return absolute


def normalize_runtime_relative_path(base_url: str, path: str) -> str:
    trimmed = path.strip()
    if trimmed == "":
        return ""

    parsed_path = urlsplit(trimmed)
    prepend_sandbox = should_prepend_sandbox_to_runtime_api(base_url)
    normalized_path = normalize_runtime_api_path(parsed_path.path, prepend_sandbox)
    relative_path = normalized_path.lstrip("/")
    return urlunsplit(
        ("", "", relative_path, parsed_path.query, parsed_path.fragment)
    )


def resolve_runtime_transport_target(
    base_url: str,
    path: str,
    runtime_proxy_override: Optional[str] = None,
) -> RuntimeTransportTarget:
    normalized_base = base_url if base_url.endswith("/") else f"{base_url}/"
    url = urljoin(normalized_base, normalize_runtime_relative_path(base_url, path))

    if not runtime_proxy_override:
        return RuntimeTransportTarget(url=url)

    override_raw = (
        runtime_proxy_override
        if has_scheme(runtime_proxy_override)
        else f"{urlsplit(url).scheme}://{runtime_proxy_override}"
    )
    original = urlsplit(url)
    override = urlsplit(override_raw)
    rewritten = urlunsplit(
        (
            override.scheme or original.scheme,
            override.netloc or original.netloc,
            original.path,
            original.query,
            original.fragment,
        )
    )
    runtime_host = urlsplit(base_url).netloc
    return RuntimeTransportTarget(url=rewritten, host_header=runtime_host)


def to_websocket_transport_target(
    base_url: str,
    path: str,
    runtime_proxy_override: Optional[str] = None,
) -> RuntimeTransportTarget:
    normalized_base = base_url if base_url.endswith("/") else f"{base_url}/"
    url = urljoin(normalized_base, normalize_runtime_relative_path(base_url, path))
    parts = urlsplit(url)
    scheme = parts.scheme
    if scheme == "https":
        scheme = "wss"
    elif scheme == "http":
        scheme = "ws"
    websocket_url = urlunsplit(
        (scheme, parts.netloc, parts.path, parts.query, parts.fragment)
    )

    if not runtime_proxy_override:
        return RuntimeTransportTarget(url=websocket_url)

    override = urlsplit(
        runtime_proxy_override
        if has_scheme(runtime_proxy_override)
        else f"{parts.scheme}://{runtime_proxy_override}"
    )
    connect_port = override.port
    if connect_port is None:
        if override.scheme in {"https", "wss"}:
            connect_port = 443
        elif override.scheme in {"http", "ws"}:
            connect_port = 80

    return RuntimeTransportTarget(
        url=websocket_url,
        connect_host=override.hostname,
        connect_port=connect_port,
    )


def normalize_network_error(
    error: BaseException,
    service: HyperbrowserService,
    default_message: str,
) -> HyperbrowserError:
    if isinstance(error, HyperbrowserError):
        return error

    return HyperbrowserError(
        str(error) if str(error) else default_message,
        retryable=is_retryable_network_error(error),
        service=service,
        cause=error,
        original_error=error if isinstance(error, Exception) else None,
    )


def build_headers(
    token: str,
    extra_headers: Optional[Dict[str, str]] = None,
    host_header: Optional[str] = None,
) -> Dict[str, str]:
    headers: Dict[str, str] = {
        "Authorization": f"Bearer {token}",
    }
    if extra_headers:
        for key, value in extra_headers.items():
            if value is not None:
                headers[key] = str(value)
    if host_header and "Host" not in headers and "host" not in headers:
        headers["Host"] = host_header
    return headers
