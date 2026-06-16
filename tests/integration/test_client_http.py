import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from hyperbrowser import AsyncHyperbrowser, Hyperbrowser
from hyperbrowser.models.scrape import ScrapeOptions, StartScrapeJobParams
from hyperbrowser.models.session import (
    CaptchaEvaluationParams,
    CreateSessionParams,
    ImageCaptchaParam,
    StartSessionFromSnapshotParams,
    UpdateSessionSolveCaptchasParams,
)

SESSION_ID = "52dd29fb-75a2-43f9-9831-8ff377fedb0a"
SNAPSHOT_ID = "11111111-1111-4111-8111-111111111111"


def _read_json_body(handler: BaseHTTPRequestHandler):
    content_length = int(handler.headers.get("Content-Length", "0"))
    if content_length <= 0:
        return None
    return json.loads(handler.rfile.read(content_length).decode("utf-8"))


def _send_json(
    handler: BaseHTTPRequestHandler, status_code: int, payload: dict
) -> None:
    encoded = json.dumps(payload).encode("utf-8")
    handler.send_response(status_code)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(encoded)))
    handler.end_headers()
    handler.wfile.write(encoded)


def _session_detail_payload() -> dict:
    return {
        "id": SESSION_ID,
        "teamId": "team_123",
        "status": "active",
        "createdAt": "2026-06-16T00:00:00.000Z",
        "updatedAt": "2026-06-16T00:00:00.000Z",
        "sessionUrl": "https://session.example.com",
        "proxyDataConsumed": "0",
        "launchState": None,
        "creditsUsed": None,
        "creditBreakdown": {
            "creditsUsed": None,
            "browserTimeCreditsUsed": None,
            "proxyDataCreditsUsed": None,
        },
        "wsEndpoint": "wss://session.example.com/devtools/browser",
        "liveUrl": "https://live.example.com",
        "token": "session-token",
    }


def _start_server():
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
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

            if self.path == "/api/scrape":
                _send_json(self, 200, {"jobId": "job_123"})
                return

            if self.path == "/api/session":
                _send_json(self, 200, _session_detail_payload())
                return

            if self.path == f"/api/session/{SESSION_ID}/snapshot":
                _send_json(
                    self,
                    200,
                    {
                        "snapshotName": f"browser-session-{SNAPSHOT_ID}",
                        "snapshotId": SNAPSHOT_ID,
                        "namespace": "team_team_123",
                        "status": "created",
                        "uploaded": False,
                        "ready": False,
                        "imageName": "browser-base",
                        "imageId": "22222222-2222-4222-8222-222222222222",
                        "imageNamespace": "default",
                    },
                )
                return

            if (
                self.path
                == f"/api/session/{SESSION_ID}/captcha/evaluate"
            ):
                _send_json(
                    self,
                    200,
                    {
                        "success": True,
                        "captcha": "recaptcha-visual",
                        "iterationsRequested": body.get("iterations", 1),
                        "iterationsRun": 1,
                        "solved": True,
                        "solvedCaptchas": ["recaptcha-visual"],
                        "pages": [
                            {
                                "url": "https://example.com",
                                "targetId": "target-123",
                                "iterationsRun": 1,
                                "solved": True,
                                "solvedCaptchas": ["recaptcha-visual"],
                                "checkedCaptchas": ["recaptcha"],
                                "captchaSolvedCounts": {"recaptcha-visual": 1},
                                "lastSolveTime": {"recaptcha-visual": 123.4},
                            }
                        ],
                    },
                )
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
                self.path == f"/api/session/{SESSION_ID}/update"
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


def _snapshot_create_params() -> CreateSessionParams:
    return CreateSessionParams(
        start_from_snapshot=StartSessionFromSnapshotParams(snapshot_id=SNAPSHOT_ID),
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


def test_sync_session_create_can_start_from_snapshot():
    server, base_url, requests = _start_server()
    client = Hyperbrowser(api_key="test-api-key", base_url=base_url)
    try:
        session = client.sessions.create(_snapshot_create_params())
    finally:
        client.close()
        server.shutdown()
        server.server_close()

    assert session.id == SESSION_ID
    assert requests == [
        {
            "method": "POST",
            "path": "/api/session",
            "api_key": "test-api-key",
            "content_type": "application/json",
            "body": {
                "useUltraStealth": False,
                "useStealth": False,
                "useProxy": False,
                "locales": ["en"],
                "solveCaptchas": False,
                "adblock": False,
                "trackers": False,
                "annoyances": False,
                "startFromSnapshot": {
                    "snapshotId": SNAPSHOT_ID,
                },
            },
        },
    ]


@pytest.mark.anyio
async def test_async_session_create_can_start_from_snapshot():
    server, base_url, requests = _start_server()
    client = AsyncHyperbrowser(api_key="test-api-key", base_url=base_url)
    try:
        session = await client.sessions.create(_snapshot_create_params())
    finally:
        await client.close()
        server.shutdown()
        server.server_close()

    assert session.id == SESSION_ID
    assert requests == [
        {
            "method": "POST",
            "path": "/api/session",
            "api_key": "test-api-key",
            "content_type": "application/json",
            "body": {
                "useUltraStealth": False,
                "useStealth": False,
                "useProxy": False,
                "locales": ["en"],
                "solveCaptchas": False,
                "adblock": False,
                "trackers": False,
                "annoyances": False,
                "startFromSnapshot": {
                    "snapshotId": SNAPSHOT_ID,
                },
            },
        },
    ]


def test_sync_session_create_snapshot_posts_empty_body_and_parses_result():
    server, base_url, requests = _start_server()
    client = Hyperbrowser(api_key="test-api-key", base_url=base_url)
    try:
        snapshot = client.sessions.create_snapshot(SESSION_ID)
    finally:
        client.close()
        server.shutdown()
        server.server_close()

    assert snapshot.snapshot_id == SNAPSHOT_ID
    assert snapshot.snapshot_name == f"browser-session-{SNAPSHOT_ID}"
    assert snapshot.namespace == "team_team_123"
    assert snapshot.status == "created"
    assert snapshot.uploaded is False
    assert snapshot.ready is False
    assert snapshot.image_name == "browser-base"
    assert requests == [
        {
            "method": "POST",
            "path": f"/api/session/{SESSION_ID}/snapshot",
            "api_key": "test-api-key",
            "content_type": "application/json",
            "body": {},
        },
    ]


@pytest.mark.anyio
async def test_async_session_create_snapshot_posts_empty_body_and_parses_result():
    server, base_url, requests = _start_server()
    client = AsyncHyperbrowser(api_key="test-api-key", base_url=base_url)
    try:
        snapshot = await client.sessions.create_snapshot(SESSION_ID)
    finally:
        await client.close()
        server.shutdown()
        server.server_close()

    assert snapshot.snapshot_id == SNAPSHOT_ID
    assert snapshot.snapshot_name == f"browser-session-{SNAPSHOT_ID}"
    assert snapshot.namespace == "team_team_123"
    assert snapshot.status == "created"
    assert snapshot.uploaded is False
    assert snapshot.ready is False
    assert snapshot.image_name == "browser-base"
    assert requests == [
        {
            "method": "POST",
            "path": f"/api/session/{SESSION_ID}/snapshot",
            "api_key": "test-api-key",
            "content_type": "application/json",
            "body": {},
        },
    ]


def test_sync_session_evaluate_captcha_triggers_manual_evaluation():
    server, base_url, requests = _start_server()
    client = Hyperbrowser(api_key="test-api-key", base_url=base_url)
    try:
        result = client.sessions.evaluate_captcha(
            SESSION_ID,
            CaptchaEvaluationParams(
                captcha_type="recaptcha-visual",
                iterations=2,
                solver_type="visual",
                image_captcha_params=[
                    ImageCaptchaParam(
                        image_selector="#captcha-img",
                        input_selector="#captcha-input",
                    )
                ],
                use_ultra_stealth=True,
            ),
        )
    finally:
        client.close()
        server.shutdown()
        server.server_close()

    assert result.success is True
    assert result.captcha == "recaptcha-visual"
    assert result.iterations_requested == 2
    assert result.pages[0].target_id == "target-123"
    assert result.pages[0].captcha_solved_counts == {"recaptcha-visual": 1}
    assert requests == [
        {
            "method": "POST",
            "path": f"/api/session/{SESSION_ID}/captcha/evaluate",
            "api_key": "test-api-key",
            "content_type": "application/json",
            "body": {
                "captchaType": "recaptcha-visual",
                "iterations": 2,
                "solverType": "visual",
                "imageCaptchaParams": [
                    {
                        "imageSelector": "#captcha-img",
                        "inputSelector": "#captcha-input",
                    }
                ],
                "useUltraStealth": True,
            },
        },
    ]


@pytest.mark.anyio
async def test_async_session_evaluate_captcha_triggers_manual_evaluation():
    server, base_url, requests = _start_server()
    client = AsyncHyperbrowser(api_key="test-api-key", base_url=base_url)
    try:
        result = await client.sessions.evaluate_captcha(
            SESSION_ID,
            CaptchaEvaluationParams(
                captcha="recaptcha",
                max_iterations=3,
                solver_type="visual",
            ),
        )
    finally:
        await client.close()
        server.shutdown()
        server.server_close()

    assert result.success is True
    assert result.solved is True
    assert result.solved_captchas == ["recaptcha-visual"]
    assert result.pages[0].last_solve_time == {"recaptcha-visual": 123.4}
    assert requests == [
        {
            "method": "POST",
            "path": f"/api/session/{SESSION_ID}/captcha/evaluate",
            "api_key": "test-api-key",
            "content_type": "application/json",
            "body": {
                "captcha": "recaptcha",
                "maxIterations": 3,
                "solverType": "visual",
            },
        },
    ]


def test_sync_session_captcha_solving_update_starts_and_stops_automatic_solving():
    server, base_url, requests = _start_server()
    client = Hyperbrowser(api_key="test-api-key", base_url=base_url)
    try:
        started = client.sessions.start_captcha_solving(
            SESSION_ID,
            UpdateSessionSolveCaptchasParams(solver_type="visual"),
        )
        stopped = client.sessions.stop_captcha_solving(
            SESSION_ID
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
            "path": f"/api/session/{SESSION_ID}/update",
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
            "path": f"/api/session/{SESSION_ID}/update",
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
            SESSION_ID,
            UpdateSessionSolveCaptchasParams(solver_type="visual"),
        )
        stopped = await client.sessions.stop_captcha_solving(
            SESSION_ID
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
            "path": f"/api/session/{SESSION_ID}/update",
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
            "path": f"/api/session/{SESSION_ID}/update",
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
