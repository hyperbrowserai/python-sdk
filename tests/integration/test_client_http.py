import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from hyperbrowser import AsyncHyperbrowser, Hyperbrowser
from hyperbrowser.models.scrape import ScrapeOptions, StartScrapeJobParams
from hyperbrowser.models.session import UpdateSessionSolveCaptchasParams


def _read_json_body(handler: BaseHTTPRequestHandler):
    content_length = int(handler.headers.get("Content-Length", "0"))
    if content_length <= 0:
        return None
    return json.loads(handler.rfile.read(content_length).decode("utf-8"))


def _send_json(handler: BaseHTTPRequestHandler, status_code: int, payload: dict) -> None:
    encoded = json.dumps(payload).encode("utf-8")
    handler.send_response(status_code)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(encoded)))
    handler.end_headers()
    handler.wfile.write(encoded)


def _start_server():
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            requests.append(
                {
                    "method": self.command,
                    "path": self.path,
                    "api_key": self.headers.get("x-api-key"),
                    "content_type": self.headers.get("content-type"),
                    "body": _read_json_body(self),
                }
            )

            if self.path == "/api/scrape":
                _send_json(self, 200, {"jobId": "job_123"})
                return

            _send_json(self, 404, {"message": f"unexpected route {self.path}"})

        def do_GET(self):
            requests.append(
                {
                    "method": self.command,
                    "path": self.path,
                    "api_key": self.headers.get("x-api-key"),
                    "content_type": self.headers.get("content-type"),
                    "body": None,
                }
            )

            if self.path == "/api/scrape/job_123/status":
                _send_json(self, 200, {"status": "completed"})
                return

            _send_json(self, 404, {"message": f"unexpected route {self.path}"})

        def do_PUT(self):
            body = _read_json_body(self)
            requests.append(
                {
                    "method": self.command,
                    "path": self.path,
                    "api_key": self.headers.get("x-api-key"),
                    "content_type": self.headers.get("content-type"),
                    "body": body,
                }
            )

            if (
                self.path
                == "/api/session/52dd29fb-75a2-43f9-9831-8ff377fedb0a/update"
                and body.get("type") == "solveCaptchas"
            ):
                _send_json(
                    self,
                    200,
                    {
                        "success": True,
                        "solveCaptchas": bool(body.get("params", {}).get("enabled")),
                    },
                )
                return

            _send_json(self, 404, {"message": f"unexpected route {self.path}"})

        def log_message(self, format, *args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://127.0.0.1:{server.server_address[1]}", requests


def _scrape_params() -> StartScrapeJobParams:
    return StartScrapeJobParams(
        url="https://example.com",
        scrape_options=ScrapeOptions(formats=["markdown"]),
    )


def test_sync_client_uses_configured_api_endpoint_and_parses_responses():
    server, base_url, requests = _start_server()
    client = Hyperbrowser(api_key="test-api-key", base_url=base_url)
    try:
        started = client.scrape.start(_scrape_params())
        status = client.scrape.get_status(started.job_id)
    finally:
        client.close()
        server.shutdown()
        server.server_close()

    assert started.job_id == "job_123"
    assert status.status == "completed"
    assert requests == [
        {
            "method": "POST",
            "path": "/api/scrape",
            "api_key": "test-api-key",
            "content_type": "application/json",
            "body": {
                "url": "https://example.com",
                "scrapeOptions": {
                    "formats": ["markdown"],
                },
            },
        },
        {
            "method": "GET",
            "path": "/api/scrape/job_123/status",
            "api_key": "test-api-key",
            "content_type": None,
            "body": None,
        },
    ]


@pytest.mark.anyio
async def test_async_client_uses_configured_api_endpoint_and_parses_responses():
    server, base_url, requests = _start_server()
    client = AsyncHyperbrowser(api_key="test-api-key", base_url=base_url)
    try:
        started = await client.scrape.start(_scrape_params())
        status = await client.scrape.get_status(started.job_id)
    finally:
        await client.close()
        server.shutdown()
        server.server_close()

    assert started.job_id == "job_123"
    assert status.status == "completed"
    assert requests == [
        {
            "method": "POST",
            "path": "/api/scrape",
            "api_key": "test-api-key",
            "content_type": "application/json",
            "body": {
                "url": "https://example.com",
                "scrapeOptions": {
                    "formats": ["markdown"],
                },
            },
        },
        {
            "method": "GET",
            "path": "/api/scrape/job_123/status",
            "api_key": "test-api-key",
            "content_type": None,
            "body": None,
        },
    ]


def test_sync_session_captcha_solving_update_starts_and_stops_automatic_solving():
    server, base_url, requests = _start_server()
    client = Hyperbrowser(api_key="test-api-key", base_url=base_url)
    try:
        started = client.sessions.start_captcha_solving(
            "52dd29fb-75a2-43f9-9831-8ff377fedb0a",
            UpdateSessionSolveCaptchasParams(solver_type="visual"),
        )
        stopped = client.sessions.stop_captcha_solving(
            "52dd29fb-75a2-43f9-9831-8ff377fedb0a"
        )
    finally:
        client.close()
        server.shutdown()
        server.server_close()

    assert started.success is True
    assert started.solve_captchas is True
    assert stopped.success is True
    assert stopped.solve_captchas is False
    assert requests == [
        {
            "method": "PUT",
            "path": "/api/session/52dd29fb-75a2-43f9-9831-8ff377fedb0a/update",
            "api_key": "test-api-key",
            "content_type": "application/json",
            "body": {
                "type": "solveCaptchas",
                "params": {
                    "enabled": True,
                    "solverType": "visual",
                },
            },
        },
        {
            "method": "PUT",
            "path": "/api/session/52dd29fb-75a2-43f9-9831-8ff377fedb0a/update",
            "api_key": "test-api-key",
            "content_type": "application/json",
            "body": {
                "type": "solveCaptchas",
                "params": {
                    "enabled": False,
                },
            },
        },
    ]


@pytest.mark.anyio
async def test_async_session_captcha_solving_update_starts_and_stops_automatic_solving():
    server, base_url, requests = _start_server()
    client = AsyncHyperbrowser(api_key="test-api-key", base_url=base_url)
    try:
        started = await client.sessions.start_captcha_solving(
            "52dd29fb-75a2-43f9-9831-8ff377fedb0a",
            UpdateSessionSolveCaptchasParams(solver_type="visual"),
        )
        stopped = await client.sessions.stop_captcha_solving(
            "52dd29fb-75a2-43f9-9831-8ff377fedb0a"
        )
    finally:
        await client.close()
        server.shutdown()
        server.server_close()

    assert started.success is True
    assert started.solve_captchas is True
    assert stopped.success is True
    assert stopped.solve_captchas is False
    assert requests == [
        {
            "method": "PUT",
            "path": "/api/session/52dd29fb-75a2-43f9-9831-8ff377fedb0a/update",
            "api_key": "test-api-key",
            "content_type": "application/json",
            "body": {
                "type": "solveCaptchas",
                "params": {
                    "enabled": True,
                    "solverType": "visual",
                },
            },
        },
        {
            "method": "PUT",
            "path": "/api/session/52dd29fb-75a2-43f9-9831-8ff377fedb0a/update",
            "api_key": "test-api-key",
            "content_type": "application/json",
            "body": {
                "type": "solveCaptchas",
                "params": {
                    "enabled": False,
                },
            },
        },
    ]
