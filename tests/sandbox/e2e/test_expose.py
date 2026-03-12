import time

from hyperbrowser.models import SandboxExecParams, SandboxExposeParams

from tests.helpers.config import create_client
from tests.helpers.errors import expect_hyperbrowser_error
from tests.helpers.http import fetch_runtime_url
from tests.helpers.sandbox import (
    default_sandbox_params,
    stop_sandbox_if_running,
    wait_for_runtime_ready,
)

client = create_client()
HTTP_PORT = 3210


def _wait_for_http_response(url: str, *, headers=None, predicate, attempts: int = 15):
    last_status = 0
    last_body = ""

    for attempt in range(1, attempts + 1):
        try:
            response = fetch_runtime_url(url, headers=headers)
            body = response.text
            last_status = response.status_code
            last_body = body
            if predicate(response.status_code, body):
                return response.status_code, body
        except Exception as error:  # pragma: no cover - network edge in e2e
            last_body = str(error)

        if attempt < attempts:
            time.sleep(0.2 * attempt)

    raise AssertionError(
        f"did not receive expected response for {url}; "
        f"last status={last_status}, last body={last_body!r}"
    )


def test_sandbox_expose_e2e():
    sandbox = None
    server_process = None

    try:
        sandbox = client.sandboxes.create(default_sandbox_params("py-sdk-expose"))
        wait_for_runtime_ready(sandbox)

        server_process = sandbox.processes.start(
            SandboxExecParams(
                command="node",
                args=[
                    "-e",
                    " ".join(
                        [
                            "const http = require('http');",
                            f"const port = {HTTP_PORT};",
                            "const server = http.createServer((req, res) => {",
                            "  res.writeHead(200, {'content-type': 'text/plain'});",
                            "  res.end(`sdk-exposed:${req.method}:${req.url}`);",
                            "});",
                            "server.listen(port, '0.0.0.0', () => {",
                            "  console.log(`listening:${port}`);",
                            "});",
                            "process.on('SIGTERM', () => server.close(() => process.exit(0)));",
                            "process.on('SIGINT', () => server.close(() => process.exit(0)));",
                        ]
                    ),
                ],
            )
        )

        token = sandbox.to_dict()["token"]
        assert token
        _wait_for_http_response(
            sandbox.get_exposed_url(HTTP_PORT),
            headers={"Authorization": f"Bearer {token}"},
            predicate=lambda status, _: status == 403,
        )

        expect_hyperbrowser_error(
            "reserved receiver port expose",
            lambda: sandbox.expose(SandboxExposeParams(port=4001)),
            status_code=400,
            service="control",
            retryable=False,
            message_includes="cannot be exposed",
        )

        exposure = sandbox.expose(SandboxExposeParams(port=HTTP_PORT, auth=False))
        assert exposure.port == HTTP_PORT
        assert exposure.auth is False
        assert exposure.url == sandbox.get_exposed_url(HTTP_PORT)

        status, body = _wait_for_http_response(
            exposure.url,
            predicate=lambda response_status, response_body: (
                response_status == 200 and "sdk-exposed:GET:/" in response_body
            ),
        )
        assert status == 200
        assert "sdk-exposed:GET:/" in body

        exposure = sandbox.expose(SandboxExposeParams(port=HTTP_PORT, auth=True))
        assert exposure.auth is True

        status, _ = _wait_for_http_response(
            exposure.url,
            predicate=lambda response_status, _: response_status == 401,
        )
        assert status == 401

        sandbox.refresh()
        token = sandbox.to_dict()["token"]
        assert token
        status, body = _wait_for_http_response(
            exposure.url,
            headers={"Authorization": f"Bearer {token}"},
            predicate=lambda response_status, response_body: (
                response_status == 200 and "sdk-exposed:GET:/" in response_body
            ),
        )
        assert status == 200
        assert "sdk-exposed:GET:/" in body
    finally:
        if server_process is not None:
            try:
                server_process.kill()
            except Exception:
                pass
        stop_sandbox_if_running(sandbox)
