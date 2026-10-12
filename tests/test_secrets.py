import base64
import json
import asyncio
import time

import httpx
import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from hyperbrowser.client.managers.async_manager.sandbox import (
    SandboxManager as AsyncSandboxManager,
)
from hyperbrowser.client.managers.async_manager.sandboxes.sandbox_processes import (
    SandboxProcessesApi as AsyncSandboxProcessesApi,
)
from hyperbrowser.client.managers.async_manager.secret import (
    SecretManager as AsyncSecretManager,
)
from hyperbrowser.client.managers.sync_manager.sandbox import SandboxManager
from hyperbrowser.client.managers.sync_manager.sandboxes.sandbox_processes import (
    SandboxProcessesApi,
)
from hyperbrowser.client.managers.sync_manager.secret import SecretManager
from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.models import (
    CreateSandboxParams,
    CreateSecretParams,
    SandboxDetail,
    SandboxExecParams,
    SandboxSnapshotSummary,
    StartSandboxFromSnapshotParams,
)
from hyperbrowser.sandbox_common import ensure_response_ok
from hyperbrowser.secrets_common import (
    SecretsSealer,
    looks_like_secret_id,
    request_may_have_arrived,
    secret_value_bytes,
    secrets_key_id,
)
from tests.test_sandbox_wire_contract import (
    SANDBOX_DETAIL_PAYLOAD,
    SNAPSHOT_LIST_PAYLOAD,
)

SECRET_ID = "8a0c7a5e-4d3b-4a5e-9b8f-0b4c7e7d2a11"
UUID_SHAPED_NAME = "0f6b7c2e-1111-4222-8333-944455556666"
CONTEXT = "hb-secret:v1:team_1:" + SECRET_ID


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


@pytest.fixture(scope="module")
def private_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=3072)


def _public_key_payload(key, kid=None):
    numbers = key.public_key().public_numbers()
    n = numbers.n.to_bytes((numbers.n.bit_length() + 7) // 8, "big")
    return {
        "kid": kid or secrets_key_id(key.public_key()),
        "alg": "RSA-OAEP-256",
        "enc": "A256GCM",
        "jwk": {"kty": "RSA", "n": _b64url(n), "e": "AQAB"},
    }


def _open(private_key, envelope: str):
    protected, encrypted_key, iv, ciphertext, tag = envelope.split(".")
    cek = private_key.decrypt(
        _b64url_decode(encrypted_key),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    value = AESGCM(cek).decrypt(
        _b64url_decode(iv),
        _b64url_decode(ciphertext) + _b64url_decode(tag),
        protected.encode("ascii"),
    )
    return json.loads(_b64url_decode(protected)), value


def _secret(name="provider-key", secret_id=SECRET_ID, latest=None):
    return {
        "id": secret_id,
        "name": name,
        "description": "",
        "encryptionContext": CONTEXT,
        "latestVersion": latest,
        "createdAt": "2026-10-01T00:00:00Z",
        "updatedAt": "2026-10-01T00:00:00Z",
    }


class ScriptedHTTPClient:
    """Answers control API requests from (method, path) routes."""

    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def _respond(self, method, url, params, json_body):
        path = url.replace("https://api.example.com/api", "")
        self.calls.append(
            {"method": method, "path": path, "params": params, "json": json_body}
        )
        route = self.routes.get((method, path))
        if route is None:
            raise AssertionError(f"Unexpected request {method} {path}")
        if callable(route):
            route = route(params, json_body)
        if isinstance(route, BaseException):
            raise route
        if isinstance(route, httpx.Response):
            return route
        status, payload = route
        return httpx.Response(status, json=payload, request=httpx.Request(method, url))

    def request(self, method, url, params=None, json=None):
        return self._respond(method, url, params, json)


class AsyncScriptedHTTPClient(ScriptedHTTPClient):
    async def request(self, method, url, params=None, json=None):
        return self._respond(method, url, params, json)


class FakeClient:
    def __init__(self, http_client):
        self.transport = type("Transport", (), {"client": http_client})()
        self.config = type("Config", (), {"runtime_proxy_override": None})()
        self.timeout = 30

    def _build_url(self, path: str) -> str:
        return f"https://api.example.com/api{path}"


# --- value rules and encryption ---


def test_secret_values_follow_the_platform_rules():
    assert secret_value_bytes("line\n") == b"line\n"
    assert secret_value_bytes(b"x" * 32768) == b"x" * 32768
    for bad in ["", b"x" * 32769, b"\xff\xfe", "a\x00b"]:
        with pytest.raises(HyperbrowserError) as error:
            secret_value_bytes(bad)
        assert error.value.code == "invalid_secret_value"


def test_sealed_values_round_trip_and_bind_the_encryption_context(private_key):
    sealer = SecretsSealer(_public_key_payload(private_key))
    envelope = sealer.seal(CONTEXT, "s3cr3t\n")

    assert len(envelope.split(".")) == 5
    assert "=" not in envelope
    header, value = _open(private_key, envelope)
    assert header == {
        "alg": "RSA-OAEP-256",
        "enc": "A256GCM",
        "kid": secrets_key_id(private_key.public_key()),
        "ctx": CONTEXT,
    }
    assert value == b"s3cr3t\n"


def test_keys_that_do_not_match_their_id_or_policy_are_refused(private_key):
    with pytest.raises(HyperbrowserError, match="does not match its key ID"):
        SecretsSealer(_public_key_payload(private_key, kid="not-the-thumbprint"))

    small = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with pytest.raises(HyperbrowserError, match="at least 3072-bit"):
        SecretsSealer(_public_key_payload(small))

    unsupported = dict(_public_key_payload(private_key), alg="RSA-OAEP")
    with pytest.raises(HyperbrowserError, match="Unsupported secrets key"):
        SecretsSealer(unsupported)


# --- the secrets manager ---


def test_list_get_update_and_delete_use_the_secrets_routes():
    http = ScriptedHTTPClient(
        {
            ("GET", "/secrets"): (
                200,
                {"secrets": [_secret()], "totalCount": 1, "page": 1, "perPage": 20},
            ),
            ("GET", f"/secrets/{SECRET_ID}"): (
                200,
                dict(
                    _secret(latest=2),
                    versions=[
                        {"version": 1, "kid": "k", "createdAt": "2026-10-01T00:00:00Z"},
                        {"version": 2, "kid": "k", "createdAt": "2026-10-02T00:00:00Z"},
                    ],
                ),
            ),
            ("PATCH", f"/secrets/{SECRET_ID}"): (
                200,
                dict(_secret(), description="rotated monthly"),
            ),
            ("DELETE", f"/secrets/{SECRET_ID}/versions/1"): (
                200,
                {"deleted": True, "version": 1},
            ),
            ("DELETE", f"/secrets/{SECRET_ID}"): (
                200,
                {"deleted": True, "id": SECRET_ID, "name": "provider-key"},
            ),
        }
    )
    manager = SecretManager(FakeClient(http))

    listing = manager.list({"search": "provider", "page": 1, "limit": 20})
    assert listing.total_count == 1 and listing.secrets[0].name == "provider-key"
    assert http.calls[0]["params"] == {"search": "provider", "page": 1, "limit": 20}

    http.calls.clear()
    detail = manager.get(SECRET_ID)
    assert [v.version for v in detail.versions] == [1, 2]
    # Found by ID: one request, no name search.
    assert [c["path"] for c in http.calls] == [f"/secrets/{SECRET_ID}"]

    updated = manager.update(SECRET_ID, {"description": "rotated monthly"})
    assert updated.description == "rotated monthly"
    assert http.calls[-1]["json"] == {"description": "rotated monthly"}

    assert manager.delete_version(SECRET_ID, 1).version == 1
    assert manager.delete(SECRET_ID).name == "provider-key"


def test_names_resolve_by_exact_match_and_fetch_the_detail_once():
    http = ScriptedHTTPClient(
        {
            ("GET", "/secrets"): (
                200,
                {
                    "secrets": [
                        _secret(name="provider-key-old", secret_id="other"),
                        _secret(),
                    ],
                    "totalCount": 2,
                },
            ),
            ("GET", f"/secrets/{SECRET_ID}"): (200, dict(_secret(), versions=[])),
        }
    )
    manager = SecretManager(FakeClient(http))

    assert manager.get("provider-key").id == SECRET_ID
    assert http.calls[0]["params"] == {"search": "provider-key", "limit": 100}
    assert [c["path"] for c in http.calls] == ["/secrets", f"/secrets/{SECRET_ID}"]

    with pytest.raises(HyperbrowserError) as error:
        manager.get("provider")
    assert error.value.status_code == 404
    assert error.value.code == "SECRET_NOT_FOUND"


def test_a_uuid_shaped_name_falls_back_to_a_name_lookup_after_a_404():
    named = _secret(name=UUID_SHAPED_NAME)
    http = ScriptedHTTPClient(
        {
            ("GET", f"/secrets/{UUID_SHAPED_NAME}"): (
                404,
                {"code": "SECRET_NOT_FOUND", "message": "Secret not found"},
            ),
            ("GET", "/secrets"): (200, {"secrets": [named], "totalCount": 1}),
            ("DELETE", f"/secrets/{SECRET_ID}"): (200, {"deleted": True}),
        }
    )
    manager = SecretManager(FakeClient(http))

    manager.delete(UUID_SHAPED_NAME)

    assert [c["path"] for c in http.calls] == [
        f"/secrets/{UUID_SHAPED_NAME}",
        "/secrets",
        f"/secrets/{SECRET_ID}",
    ]


def test_other_id_lookup_errors_are_reported_without_a_name_search():
    http = ScriptedHTTPClient(
        {("GET", f"/secrets/{SECRET_ID}"): (500, {"message": "boom"})}
    )
    manager = SecretManager(FakeClient(http))

    with pytest.raises(HyperbrowserError) as error:
        manager.get(SECRET_ID)

    assert error.value.status_code == 500
    assert all(c["path"] != "/secrets" for c in http.calls)


def test_create_with_a_value_uploads_only_an_envelope_bound_to_the_new_secret(
    private_key,
):
    http = ScriptedHTTPClient(
        {
            ("GET", "/secrets/public-key"): (200, _public_key_payload(private_key)),
            ("POST", "/secrets"): (201, _secret()),
            ("POST", f"/secrets/{SECRET_ID}/versions"): (
                201,
                {"version": 1, "kid": "k", "createdAt": "2026-10-01T00:00:00Z"},
            ),
        }
    )
    manager = SecretManager(FakeClient(http))

    secret = manager.create(
        CreateSecretParams(name="provider-key", description="d", value="v\n")
    )

    assert secret.latest_version == 1
    assert [c["path"] for c in http.calls] == [
        "/secrets/public-key",
        "/secrets",
        f"/secrets/{SECRET_ID}/versions",
    ]
    assert http.calls[1]["json"] == {"name": "provider-key", "description": "d"}
    upload = http.calls[2]["json"]
    assert set(upload) == {"envelope"}
    header, value = _open(private_key, upload["envelope"])
    assert header["ctx"] == CONTEXT and value == b"v\n"


def test_create_checks_the_value_and_key_before_creating(private_key):
    http = ScriptedHTTPClient(
        {
            ("GET", "/secrets/public-key"): (
                200,
                _public_key_payload(private_key, kid="wrong"),
            ),
        }
    )
    manager = SecretManager(FakeClient(http))

    with pytest.raises(HyperbrowserError, match="NUL"):
        manager.create({"name": "provider-key", "value": "a\x00"})
    with pytest.raises(HyperbrowserError, match="key ID"):
        manager.create({"name": "provider-key", "value": "ok"})
    assert all(c["path"] != "/secrets" for c in http.calls)


def test_a_failed_upload_after_create_reports_the_partial_create(private_key):
    http = ScriptedHTTPClient(
        {
            ("GET", "/secrets/public-key"): (200, _public_key_payload(private_key)),
            ("POST", "/secrets"): (201, _secret()),
            ("POST", f"/secrets/{SECRET_ID}/versions"): (
                409,
                {"code": "SECRET_KEY_OUTDATED", "message": "key rotated"},
            ),
        }
    )
    manager = SecretManager(FakeClient(http))

    with pytest.raises(HyperbrowserError) as error:
        manager.create({"name": "provider-key", "value": "v"})

    assert error.value.code == "secret_value_not_stored"
    assert error.value.retryable is False
    assert error.value.details == {"secretId": SECRET_ID, "name": "provider-key"}
    assert error.value.cause.code == "SECRET_KEY_OUTDATED"
    assert "add_version" in str(error.value)


@pytest.mark.anyio
async def test_async_secrets_manager_resolves_names_and_adds_versions(private_key):
    http = AsyncScriptedHTTPClient(
        {
            ("GET", "/secrets"): (200, {"secrets": [_secret()], "totalCount": 1}),
            ("GET", "/secrets/public-key"): (200, _public_key_payload(private_key)),
            ("POST", f"/secrets/{SECRET_ID}/versions"): (
                201,
                {"version": 3, "kid": "k"},
            ),
            ("GET", f"/secrets/{SECRET_ID}"): (200, dict(_secret(), versions=[])),
        }
    )
    manager = AsyncSecretManager(FakeClient(http))

    version = await manager.add_version("provider-key", b"next")
    assert version.version == 3
    _, value = _open(private_key, http.calls[-1]["json"]["envelope"])
    assert value == b"next"
    assert (await manager.get("provider-key")).id == SECRET_ID


# --- sandbox create and response fields ---


def test_sandbox_create_sends_secret_references_for_image_launches():
    params = CreateSandboxParams(
        image_name="node",
        secrets={"API_KEY": "provider-key", "OTHER": {"name": "o", "version": 2}},
    )
    assert params.model_dump(by_alias=True, exclude_none=True) == {
        "imageName": "node",
        "secrets": {
            "API_KEY": {"name": "provider-key"},
            "OTHER": {"name": "o", "version": 2},
        },
    }

    with pytest.raises(ValueError, match="only supported for image launches"):
        CreateSandboxParams(snapshot_name="snap", secrets={"API_KEY": "k"})
    with pytest.raises(ValueError):
        StartSandboxFromSnapshotParams(snapshot_name="snap", secrets={"A": "k"})


def test_contains_secrets_is_decoded():
    assert SandboxDetail(**SANDBOX_DETAIL_PAYLOAD).contains_secrets is False
    detail = SandboxDetail(**dict(SANDBOX_DETAIL_PAYLOAD, containsSecrets=True))
    assert detail.contains_secrets is True
    snapshot = dict(SNAPSHOT_LIST_PAYLOAD["snapshots"][0], containsSecrets=True)
    assert SandboxSnapshotSummary(**snapshot).contains_secrets is True


# --- processes with secrets ---

AGENT_PROCESS = {
    "id": "proc_9",
    "status": "running",
    "command": "node app.js",
    "cwd": "/app",
    "pid": 42,
    "exit_code": None,
    "started_at": 1700,
    "completed_at": None,
}
RESOLVED = [
    {"env": "API_KEY", "name": "provider-key", "secretId": SECRET_ID, "version": 2}
]
RESULT = {
    "id": "proc_9",
    "status": "exited",
    "exit_code": 0,
    "stdout": "ok\n",
    "stderr": "",
    "started_at": 1700,
    "completed_at": 1800,
}


class RuntimeScript:
    """A runtime transport that answers stdin and wait from a script."""

    def __init__(self, stdin=None, waits=()):
        self._timeout = 30
        self.stdin = stdin
        self.waits = list(waits)
        self.calls = []

    def request_json(self, path, *, method="GET", json_body=None, **kwargs):
        self.calls.append({"path": path, "method": method, "json": json_body, **kwargs})
        if path.endswith("/stdin"):
            if self.stdin is not None:
                raise self.stdin
            return {"success": True}
        if path.endswith("/wait"):
            step = self.waits.pop(0)
            if isinstance(step, BaseException):
                raise step
            return {"result": step}
        if path.endswith("/proc_9") and method == "GET":
            return {"process": AGENT_PROCESS}
        raise AssertionError(path)

    def stream_sse(self, *args, **kwargs):
        raise AssertionError("secret starts must not use the runtime start")


class AsyncRuntimeScript(RuntimeScript):
    async def request_json(self, path, **kwargs):
        return RuntimeScript.request_json(self, path, **kwargs)


def _status_error(status):
    return HyperbrowserError("x", status_code=status, service="runtime")


def test_exec_with_secrets_starts_through_the_control_api_and_waits():
    starts = []
    runtime = RuntimeScript(
        stdin=_status_error(409),
        waits=[_status_error(408), _status_error(408), RESULT],
    )

    def start(payload):
        starts.append(payload)
        return {"process": AGENT_PROCESS, "secrets": RESOLVED}

    api = SandboxProcessesApi(runtime, start, "sbx_123")
    result = api.exec(
        {"command": "node", "args": ["app.js"], "env": {"MODE": "prod"}},
        cwd="/app",
        timeout_sec=5,
        run_as="root",
        secrets={"API_KEY": "provider-key", "OTHER": {"name": "o", "version": 2}},
    )

    assert result.stdout == "ok\n" and result.exit_code == 0
    assert starts == [
        {
            "command": "node app.js",
            "cwd": "/app",
            "env": {"MODE": "prod"},
            "timeoutMs": 5000,
            "runAs": "root",
            "secrets": {
                "API_KEY": {"name": "provider-key"},
                "OTHER": {"name": "o", "version": 2},
            },
        }
    ]
    assert [c["path"] for c in runtime.calls] == [
        "/sandbox/processes/proc_9/stdin",
        "/sandbox/processes/proc_9/wait",
        "/sandbox/processes/proc_9/wait",
        "/sandbox/processes/proc_9/wait",
    ]
    assert runtime.calls[0]["json"] == {"eof": True}
    assert runtime.calls[1]["json"]["timeoutMs"] == 15000


def test_start_with_secrets_exposes_the_resolved_versions():
    api = SandboxProcessesApi(
        RuntimeScript(),
        lambda payload: {"process": AGENT_PROCESS, "secrets": RESOLVED},
        "sbx_123",
    )

    handle = api.start("node app.js", secrets={"API_KEY": "provider-key"})

    assert handle.id == "proc_9" and handle.status == "running"
    assert handle.secrets[0].secret_id == SECRET_ID
    assert handle.secrets[0].version == 2


def test_env_and_secrets_may_not_set_the_same_variable():
    api = SandboxProcessesApi(RuntimeScript(), lambda payload: {}, "sbx_123")

    with pytest.raises(HyperbrowserError, match="either env or secrets"):
        api.start("env", env={"API_KEY": "x"}, secrets={"API_KEY": "provider-key"})


def test_a_failure_after_the_start_names_the_running_process():
    runtime = RuntimeScript(waits=[_status_error(502)])
    api = SandboxProcessesApi(
        runtime,
        lambda payload: {"process": AGENT_PROCESS, "secrets": RESOLVED},
        "sbx_123",
    )

    with pytest.raises(HyperbrowserError) as error:
        api.exec("node app.js", secrets={"API_KEY": "provider-key"})

    assert error.value.code == "secret_process_failed"
    assert error.value.retryable is False
    assert error.value.details == {"processId": "proc_9", "sandboxId": "sbx_123"}


@pytest.mark.anyio
async def test_async_exec_with_secrets_waits_through_expired_waits():
    runtime = AsyncRuntimeScript(waits=[_status_error(408), RESULT])

    async def start(payload):
        return {"process": AGENT_PROCESS, "secrets": RESOLVED}

    api = AsyncSandboxProcessesApi(runtime, start, "sbx_123")
    result = await api.exec("node app.js", secrets={"API_KEY": "provider-key"})

    assert result.stdout == "ok\n"
    assert len([c for c in runtime.calls if c["path"].endswith("/wait")]) == 2


def _sandbox_manager(routes, async_client=False):
    http = (AsyncScriptedHTTPClient if async_client else ScriptedHTTPClient)(routes)
    cls = AsyncSandboxManager if async_client else SandboxManager
    return cls(FakeClient(http)), http


def test_sandbox_handles_route_secret_starts_to_the_control_api():
    manager, http = _sandbox_manager(
        {
            ("POST", "/sandbox/sbx_123/processes"): (
                200,
                {"process": AGENT_PROCESS, "secrets": RESOLVED},
            )
        }
    )
    sandbox = manager.attach(SandboxDetail(**SANDBOX_DETAIL_PAYLOAD))

    handle = sandbox.processes.start("node app.js", secrets={"API_KEY": "k"})

    assert handle.id == "proc_9"
    assert http.calls[0]["json"] == {
        "command": "node app.js",
        "secrets": {"API_KEY": {"name": "k"}},
    }


def test_a_start_without_a_process_id_is_an_unknown_outcome():
    manager, _ = _sandbox_manager(
        {("POST", "/sandbox/sbx_123/processes"): (200, {"process": {}})}
    )

    with pytest.raises(HyperbrowserError) as error:
        manager.start_secret_process("sbx_123", {"command": "x", "secrets": {}})

    assert error.value.code == "secret_process_outcome_unknown"


@pytest.mark.anyio
@pytest.mark.parametrize("async_client", [False, True])
@pytest.mark.parametrize("process_id", [42, True, " "])
async def test_invalid_process_ids_are_unknown_outcomes(async_client, process_id):
    manager, http = _sandbox_manager(
        {("POST", "/sandbox/sbx_123/processes"): (200, {"process": {"id": process_id}})},
        async_client=async_client,
    )
    with pytest.raises(HyperbrowserError) as error:
        result = manager.start_secret_process("sbx_123", {"command": "x"})
        if async_client:
            await result
    assert error.value.code == "secret_process_outcome_unknown"
    assert error.value.retryable is False
    assert len(http.calls) == 1


def test_a_timed_out_start_is_an_unknown_outcome_but_a_refused_one_is_not():
    timed_out = httpx.ReadTimeout("timed out")
    manager, _ = _sandbox_manager({("POST", "/sandbox/sbx_123/processes"): timed_out})
    with pytest.raises(HyperbrowserError) as error:
        manager.start_secret_process("sbx_123", {"command": "x"})
    assert error.value.code == "secret_process_outcome_unknown"
    assert error.value.retryable is False

    refused = httpx.ConnectError("refused")
    manager, _ = _sandbox_manager({("POST", "/sandbox/sbx_123/processes"): refused})
    with pytest.raises(HyperbrowserError) as error:
        manager.start_secret_process("sbx_123", {"command": "x"})
    assert error.value.code != "secret_process_outcome_unknown"

    manager, _ = _sandbox_manager(
        {
            ("POST", "/sandbox/sbx_123/processes"): (
                502,
                {"code": "SECRET_DELIVERY_UNKNOWN", "message": "m", "retryable": False},
            )
        }
    )
    with pytest.raises(HyperbrowserError) as error:
        manager.start_secret_process("sbx_123", {"command": "x"})
    assert error.value.code == "SECRET_DELIVERY_UNKNOWN"


@pytest.mark.anyio
async def test_async_sandbox_handles_route_secret_starts_to_the_control_api():
    manager, http = _sandbox_manager(
        {
            ("POST", "/sandbox/sbx_123/processes"): (
                200,
                {"process": AGENT_PROCESS, "secrets": RESOLVED},
            )
        },
        async_client=True,
    )
    sandbox = manager.attach(SandboxDetail(**SANDBOX_DETAIL_PAYLOAD))

    handle = await sandbox.processes.start("node app.js", secrets={"API_KEY": "k"})

    assert handle.secrets[0].env == "API_KEY"
    assert http.calls[0]["path"] == "/sandbox/sbx_123/processes"


# --- error fields ---


def _error_response(status, body):
    request = httpx.Request("POST", "https://api.example.com/api/x")
    return httpx.Response(status, json=body, request=request)


def test_control_errors_honour_the_server_retryable_flag_and_code_in_error():
    with pytest.raises(HyperbrowserError) as error:
        ensure_response_ok(
            _error_response(502, {"message": "unknown", "retryable": False}),
            "control",
        )
    assert error.value.retryable is False

    with pytest.raises(HyperbrowserError) as error:
        ensure_response_ok(
            _error_response(
                403,
                {
                    "error": "API_KEY_SCOPE_DENIED",
                    "message": "denied",
                    "requiredScopes": ["secrets.use"],
                },
            ),
            "control",
        )
    assert error.value.code == "API_KEY_SCOPE_DENIED"
    assert str(error.value).startswith("denied")
    assert error.value.details["requiredScopes"] == ["secrets.use"]

    # A plain error message is not a code; runtime gateway errors keep the
    # status-code default.
    with pytest.raises(HyperbrowserError) as error:
        ensure_response_ok(_error_response(400, {"error": "Bad thing"}), "control")
    assert error.value.code is None
    with pytest.raises(HyperbrowserError) as error:
        ensure_response_ok(
            _error_response(503, {"message": "proxy", "retryable": False}),
            "runtime",
        )
    assert error.value.retryable is True


def test_request_may_have_arrived():
    assert request_may_have_arrived(httpx.ReadTimeout("t"))
    assert request_may_have_arrived(httpx.RemoteProtocolError("closed"))
    assert not request_may_have_arrived(httpx.ConnectError("refused"))
    assert not request_may_have_arrived(HyperbrowserError("x", status_code=502))
    assert request_may_have_arrived(HyperbrowserError("bad json", status_code=200))


def test_transport_errors_keep_server_codes_and_retryable_flags():
    from hyperbrowser.transport.sync import SyncTransport

    transport = SyncTransport("key")
    transport.client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                503,
                json={
                    "error": "SECRETS_NOT_CONFIGURED",
                    "message": "Secrets are not configured",
                    "retryable": False,
                },
            )
        )
    )

    with pytest.raises(HyperbrowserError) as error:
        transport.get("https://api.example.com/api/secrets/public-key")

    assert error.value.code == "SECRETS_NOT_CONFIGURED"
    assert error.value.retryable is False


@pytest.mark.parametrize("method", ["wait", "result"])
def test_secret_started_handle_waits_indefinitely_in_short_runtime_chunks(method):
    runtime = RuntimeScript(waits=[_status_error(408), _status_error(408), RESULT])
    runtime._timeout = 0.5
    api = SandboxProcessesApi(
        runtime,
        lambda payload: {"process": AGENT_PROCESS, "secrets": RESOLVED},
        "sbx_123",
    )
    handle = api.start("node app.js", secrets={"API_KEY": "provider-key"})

    assert getattr(handle, method)().stdout == "ok\n"
    assert handle.status == "exited"
    assert len(runtime.calls) == 3
    assert all(call["json"]["timeoutMs"] == 250 for call in runtime.calls)
    assert all(call["path"].endswith("/wait") for call in runtime.calls)


@pytest.mark.anyio
@pytest.mark.parametrize("method", ["wait", "result"])
async def test_async_secret_started_handle_uses_bounded_waits(method):
    runtime = AsyncRuntimeScript(waits=[_status_error(408), RESULT])
    runtime._timeout = 0.5

    async def start(payload):
        return {"process": AGENT_PROCESS, "secrets": RESOLVED}

    handle = await AsyncSandboxProcessesApi(runtime, start, "sbx_123").start(
        "node app.js", secrets={"API_KEY": "provider-key"}
    )
    assert (await getattr(handle, method)()).stdout == "ok\n"
    assert handle.status == "exited"
    assert [call["json"]["timeoutMs"] for call in runtime.calls] == [250, 250]


class ClockedRuntimeScript(RuntimeScript):
    def __init__(self, clock):
        super().__init__()
        self._timeout = 0.5
        self.clock = clock
        self.finished = False

    def request_json(self, path, *, method="GET", json_body=None, **kwargs):
        self.calls.append({"path": path, "method": method, "json": json_body, **kwargs})
        assert path.endswith("/wait")
        if self.finished:
            return {"result": RESULT}
        chunk_seconds = json_body["timeoutMs"] / 1000
        assert 0 < chunk_seconds < self._timeout
        assert chunk_seconds <= kwargs["request_timeout"]
        self.clock[0] += chunk_seconds
        raise _status_error(408)


class AsyncClockedRuntimeScript(ClockedRuntimeScript):
    async def request_json(self, path, **kwargs):
        return super().request_json(path, **kwargs)


@pytest.mark.parametrize(
    "timeouts, expected_seconds",
    [({"timeout_ms": 500}, 0.5), ({"timeout_ms": 5, "timeout_sec": 1}, 1)],
)
def test_secret_handle_wait_deadline_is_total_and_handle_can_wait_again(
    monkeypatch, timeouts, expected_seconds
):
    clock = [0.0]
    monkeypatch.setattr(time, "monotonic", lambda: clock[0])
    runtime = ClockedRuntimeScript(clock)
    handle = SandboxProcessesApi(
        runtime,
        lambda payload: {"process": AGENT_PROCESS, "secrets": RESOLVED},
        "sbx_123",
    ).start("node app.js", secrets={"API_KEY": "provider-key"})

    with pytest.raises(TimeoutError, match="Timed out waiting"):
        handle.wait(**timeouts)

    assert clock[0] == expected_seconds
    assert len(runtime.calls) == int(expected_seconds / 0.25)
    runtime.finished = True
    assert handle.result().stdout == "ok\n"


@pytest.mark.anyio
async def test_async_secret_handle_total_deadline_and_handle_reuse(monkeypatch):
    clock = [0.0]
    monkeypatch.setattr(time, "monotonic", lambda: clock[0])
    runtime = AsyncClockedRuntimeScript(clock)

    async def start(payload):
        return {"process": AGENT_PROCESS, "secrets": RESOLVED}

    handle = await AsyncSandboxProcessesApi(runtime, start, "sbx_123").start(
        "node app.js", secrets={"API_KEY": "provider-key"}
    )
    with pytest.raises(asyncio.TimeoutError):
        await handle.wait(timeout_ms=500)
    assert clock[0] == 0.5
    assert len(runtime.calls) == 2
    runtime.finished = True
    assert (await handle.result()).stdout == "ok\n"


@pytest.mark.anyio
async def test_async_local_wait_deadline_cancels_a_stalled_request():
    cancelled = []

    class StalledRuntime(AsyncRuntimeScript):
        async def request_json(self, path, **kwargs):
            try:
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                cancelled.append(path)
                raise

    async def start(payload):
        return {"process": AGENT_PROCESS, "secrets": RESOLVED}

    handle = await AsyncSandboxProcessesApi(StalledRuntime(), start, "sbx_123").start(
        "node app.js", secrets={"API_KEY": "provider-key"}
    )
    with pytest.raises(asyncio.TimeoutError):
        await handle.wait(timeout_ms=10)
    assert cancelled == ["/sandbox/processes/proc_9/wait"]


def test_reattached_ordinary_handle_keeps_its_single_wait_request():
    runtime = RuntimeScript(waits=[_status_error(408), RESULT])
    handle = SandboxProcessesApi(runtime).get("proc_9")
    with pytest.raises(HyperbrowserError) as error:
        handle.wait(timeout_ms=123, timeout_sec=2)
    assert error.value.status_code == 408
    assert runtime.calls[-1]["json"] == {"timeoutMs": 123, "timeout_sec": 2}
    assert len(runtime.waits) == 1


@pytest.mark.anyio
async def test_async_reattached_handle_keeps_its_single_wait_request():
    runtime = AsyncRuntimeScript(waits=[_status_error(408), RESULT])
    handle = await AsyncSandboxProcessesApi(runtime).get("proc_9")
    with pytest.raises(HyperbrowserError) as error:
        await handle.wait()
    assert error.value.status_code == 408
    assert runtime.calls[-1]["json"] == {"timeoutMs": None, "timeout_sec": None}
    assert len(runtime.waits) == 1


@pytest.mark.parametrize("request_type", [dict, SandboxExecParams])
@pytest.mark.parametrize(
    "fields, overrides, expected",
    [
        ({"timeout_ms": 0}, {"timeout_sec": 1}, 1000),
        ({"timeout_ms": 2000, "timeout_sec": 1}, {}, 1000),
        ({"timeout_ms": 2000, "timeout_sec": 0}, {}, 2000),
        ({"timeout_ms": 0, "timeout_sec": -1}, {}, 0),
        ({}, {}, None),
    ],
)
def test_secret_execution_timeout_matches_receiver_precedence(
    request_type, fields, overrides, expected
):
    starts = []

    def start(payload):
        starts.append(payload)
        return {"process": AGENT_PROCESS, "secrets": RESOLVED}

    SandboxProcessesApi(RuntimeScript(), start, "sbx_123").start(
        request_type(command="sleep 2", **fields),
        secrets={"API_KEY": "provider-key"},
        **overrides,
    )
    assert starts[0].get("timeoutMs") == expected


@pytest.mark.anyio
@pytest.mark.parametrize("request_type", [dict, SandboxExecParams])
async def test_async_secret_timeout_seconds_override_zero_ms(request_type):
    starts = []

    async def start(payload):
        starts.append(payload)
        return {"process": AGENT_PROCESS, "secrets": RESOLVED}

    await AsyncSandboxProcessesApi(AsyncRuntimeScript(), start, "sbx_123").start(
        request_type(command="sleep 2", timeout_ms=0),
        timeout_sec=1,
        secrets={"API_KEY": "provider-key"},
    )
    assert starts[0]["timeoutMs"] == 1000


@pytest.mark.parametrize("status", [200, 502, 503])
@pytest.mark.parametrize("body", [b"<html>Gateway error</html>", b'{"message":', b""])
def test_undecodable_secret_start_is_nonretryable_unknown_outcome(status, body):
    response = httpx.Response(
        status, content=body, request=httpx.Request("POST", "https://api.example.com")
    )
    manager, http = _sandbox_manager({("POST", "/sandbox/sbx_123/processes"): response})
    with pytest.raises(HyperbrowserError) as error:
        manager.start_secret_process("sbx_123", {"command": "x"})
    assert error.value.code == "secret_process_outcome_unknown"
    assert error.value.retryable is False
    assert error.value.details == {"sandboxId": "sbx_123"}
    assert len(http.calls) == 1


@pytest.mark.anyio
@pytest.mark.parametrize("body", [b"<html>Gateway error</html>", b'{"message":'])
async def test_async_undecodable_gateway_secret_start_has_unknown_outcome(body):
    response = httpx.Response(
        502, content=body, request=httpx.Request("POST", "https://api.example.com")
    )
    manager, http = _sandbox_manager(
        {("POST", "/sandbox/sbx_123/processes"): response}, async_client=True
    )
    with pytest.raises(HyperbrowserError) as error:
        await manager.start_secret_process("sbx_123", {"command": "x"})
    assert error.value.code == "secret_process_outcome_unknown"
    assert error.value.retryable is False
    assert isinstance(error.value.cause.cause, json.JSONDecodeError)
    assert len(http.calls) == 1


@pytest.mark.parametrize("retryable", [True, False])
def test_decoded_secret_start_error_keeps_server_retryable_flag(retryable):
    manager, http = _sandbox_manager(
        {
            ("POST", "/sandbox/sbx_123/processes"): (
                502,
                {"code": "START_FAILED", "message": "x", "retryable": retryable},
            )
        }
    )
    with pytest.raises(HyperbrowserError) as error:
        manager.start_secret_process("sbx_123", {"command": "x"})
    assert error.value.code == "START_FAILED"
    assert error.value.retryable is retryable
    assert len(http.calls) == 1


@pytest.mark.anyio
@pytest.mark.parametrize("stdin", [_status_error(409), _status_error(502)])
async def test_async_secret_exec_closes_stdin_and_preserves_process_on_failure(stdin):
    runtime = AsyncRuntimeScript(stdin=stdin, waits=[_status_error(502)])

    async def start(payload):
        return {"process": AGENT_PROCESS, "secrets": RESOLVED}

    with pytest.raises(HyperbrowserError) as error:
        await AsyncSandboxProcessesApi(runtime, start, "sbx_123").exec(
            "node app.js", secrets={"API_KEY": "provider-key"}
        )
    assert error.value.code == "secret_process_failed"
    assert error.value.retryable is False
    assert error.value.details == {"processId": "proc_9", "sandboxId": "sbx_123"}
    assert len(runtime.calls) == (2 if stdin.status_code == 409 else 1)


def test_secret_wait_handles_submillisecond_timeout_without_zero_or_busy_retry(
    monkeypatch,
):
    clock = [0.0]
    monkeypatch.setattr(time, "monotonic", lambda: clock[0])
    pauses = []

    def pause(seconds):
        pauses.append(seconds)
        clock[0] += seconds

    monkeypatch.setattr(time, "sleep", pause)
    runtime = RuntimeScript(waits=[_status_error(408)] * 4)
    runtime._timeout = 0.0005
    handle = SandboxProcessesApi(
        runtime,
        lambda payload: {"process": AGENT_PROCESS, "secrets": RESOLVED},
        "sbx_123",
    ).start("node app.js", secrets={"API_KEY": "provider-key"})
    with pytest.raises(TimeoutError):
        handle.wait(timeout_ms=1)
    assert len(runtime.calls) == 1
    assert runtime.calls[0]["json"]["timeoutMs"] == 1
    assert runtime.calls[0]["request_timeout"] == 0.0005
    assert pauses == [0.001]


@pytest.mark.parametrize("method", ["wait", "result"])
def test_secret_handle_wait_errors_retain_running_process_identifiers(method):
    runtime = RuntimeScript(waits=[_status_error(502)])
    handle = SandboxProcessesApi(
        runtime,
        lambda payload: {"process": AGENT_PROCESS, "secrets": RESOLVED},
        "sbx_123",
    ).start("node app.js", secrets={"API_KEY": "provider-key"})
    with pytest.raises(HyperbrowserError) as error:
        getattr(handle, method)()
    assert error.value.code == "secret_process_failed"
    assert error.value.details == {"processId": "proc_9", "sandboxId": "sbx_123"}
    assert error.value.retryable is False


@pytest.mark.parametrize("service", ["control", "runtime"])
def test_malformed_http_error_preserves_generic_error_parsing(service):
    response = httpx.Response(
        502,
        content=b"<html>Gateway error</html>",
        headers={"x-request-id": "req_9"},
        request=httpx.Request("POST", "https://api.example.com"),
    )
    with pytest.raises(HyperbrowserError) as error:
        ensure_response_ok(response, service)
    assert error.value.status_code == 502
    assert str(error.value).startswith("<html>Gateway error</html>")
    assert error.value.details == "<html>Gateway error</html>"
    assert error.value.code is None
    assert error.value.retryable is True
    assert error.value.request_id == "req_9"
    assert isinstance(error.value.cause, json.JSONDecodeError)


@pytest.mark.parametrize(
    "payload",
    [
        {"process": {"id": "proc_9"}, "secrets": RESOLVED},
        {"process": AGENT_PROCESS, "secrets": [{"env": "API_KEY"}]},
    ],
)
def test_secret_start_preserves_process_id_when_response_metadata_is_invalid(payload):
    api = SandboxProcessesApi(RuntimeScript(), lambda body: payload, "sbx_123")
    with pytest.raises(HyperbrowserError) as error:
        api.start("node app.js", secrets={"API_KEY": "provider-key"})
    assert error.value.code == "secret_process_failed"
    assert error.value.details == {"processId": "proc_9", "sandboxId": "sbx_123"}
    assert error.value.retryable is False


@pytest.mark.anyio
async def test_async_secret_start_keeps_process_id_on_invalid_metadata():
    async def start(payload):
        return {"process": AGENT_PROCESS, "secrets": [{"env": "API_KEY"}]}

    api = AsyncSandboxProcessesApi(AsyncRuntimeScript(), start, "sbx_123")
    with pytest.raises(HyperbrowserError) as error:
        await api.start("node app.js", secrets={"API_KEY": "provider-key"})
    assert error.value.code == "secret_process_failed"
    assert error.value.details == {"processId": "proc_9", "sandboxId": "sbx_123"}
    assert error.value.retryable is False


@pytest.mark.anyio
@pytest.mark.parametrize("retryable", [True, False])
async def test_async_decoded_secret_start_error_keeps_server_retryable_flag(retryable):
    manager, http = _sandbox_manager(
        {
            ("POST", "/sandbox/sbx_123/processes"): (
                502,
                {"code": "START_FAILED", "message": "x", "retryable": retryable},
            )
        },
        async_client=True,
    )
    with pytest.raises(HyperbrowserError) as error:
        await manager.start_secret_process("sbx_123", {"command": "x"})
    assert error.value.code == "START_FAILED"
    assert error.value.retryable is retryable
    assert len(http.calls) == 1


@pytest.mark.parametrize("method", ["wait", "result", "exec"])
def test_default_secret_wait_timeout_error_retains_process_identifiers(method):
    runtime = RuntimeScript(waits=[TimeoutError("transport timed out")])
    api = SandboxProcessesApi(
        runtime,
        lambda payload: {"process": AGENT_PROCESS, "secrets": RESOLVED},
        "sbx_123",
    )
    with pytest.raises(HyperbrowserError) as error:
        if method == "exec":
            api.exec("node app.js", secrets={"API_KEY": "provider-key"})
        else:
            handle = api.start("node app.js", secrets={"API_KEY": "provider-key"})
            getattr(handle, method)()
    assert error.value.code == "secret_process_failed"
    assert error.value.details == {"processId": "proc_9", "sandboxId": "sbx_123"}
    assert error.value.retryable is False
    assert isinstance(error.value.cause, TimeoutError)


@pytest.mark.anyio
@pytest.mark.parametrize("method", ["wait", "result", "exec"])
async def test_async_default_secret_wait_timeout_retains_identifiers(
    monkeypatch, method
):
    class DistinctAsyncTimeoutError(Exception):
        pass

    monkeypatch.setattr(asyncio, "TimeoutError", DistinctAsyncTimeoutError)
    runtime = AsyncRuntimeScript(
        waits=[DistinctAsyncTimeoutError("transport timed out")]
    )

    async def start(payload):
        return {"process": AGENT_PROCESS, "secrets": RESOLVED}

    api = AsyncSandboxProcessesApi(runtime, start, "sbx_123")
    with pytest.raises(HyperbrowserError) as error:
        if method == "exec":
            await api.exec("node app.js", secrets={"API_KEY": "provider-key"})
        else:
            handle = await api.start("node app.js", secrets={"API_KEY": "provider-key"})
            await getattr(handle, method)()
    assert error.value.code == "secret_process_failed"
    assert error.value.details == {"processId": "proc_9", "sandboxId": "sbx_123"}
    assert error.value.retryable is False
    assert isinstance(error.value.cause, DistinctAsyncTimeoutError)


@pytest.mark.anyio
@pytest.mark.parametrize(
    "expiration", ["before_request", "receiver_timeout", "stalled_request"]
)
async def test_async_deadline_preserves_distinct_asyncio_timeout_error(
    monkeypatch, expiration
):
    class DistinctAsyncTimeoutError(Exception):
        pass

    monkeypatch.setattr(asyncio, "TimeoutError", DistinctAsyncTimeoutError)
    clock = [0.0]
    runtime = AsyncClockedRuntimeScript(clock)
    if expiration == "before_request":
        clock_reads = iter([0.0, 1.0])
        monkeypatch.setattr(time, "monotonic", lambda: next(clock_reads, 1.0))
    elif expiration == "receiver_timeout":
        monkeypatch.setattr(time, "monotonic", lambda: clock[0])
    else:

        class StalledRuntime(AsyncRuntimeScript):
            async def request_json(self, path, **kwargs):
                await asyncio.sleep(10)

        runtime = StalledRuntime()

    async def start(payload):
        return {"process": AGENT_PROCESS, "secrets": RESOLVED}

    handle = await AsyncSandboxProcessesApi(runtime, start, "sbx_123").start(
        "node app.js", secrets={"API_KEY": "provider-key"}
    )
    with pytest.raises(DistinctAsyncTimeoutError):
        await handle.wait(timeout_ms=10 if expiration == "stalled_request" else 500)


# --- ID shapes, create outcomes, and server error codes ---


def test_only_hyphenated_uuids_look_like_secret_ids():
    assert looks_like_secret_id(SECRET_ID)
    assert looks_like_secret_id(SECRET_ID.upper())
    for key in [
        "a-bcdefabcdef-abcd-efab-cdefabcdefab",
        "8a0c7a5e4d3b4a5e9b8f0b4c7e7d2a11",
        "{8a0c7a5e-4d3b-4a5e-9b8f-0b4c7e7d2a1}",
        "8a0c7a5e-4d3b-4a5e-9b8f-0b4c7e7d2a1g",
    ]:
        assert not looks_like_secret_id(key)


def test_a_name_with_hyphens_in_other_places_goes_straight_to_the_name_search():
    name = "a-bcdefabcdef-abcd-efab-cdefabcdefab"
    http = ScriptedHTTPClient(
        {
            ("GET", "/secrets"): (
                200,
                {"secrets": [_secret(name=name)], "totalCount": 1},
            ),
            ("DELETE", f"/secrets/{SECRET_ID}"): (200, {"deleted": True}),
        }
    )

    SecretManager(FakeClient(http)).delete(name)

    assert [c["path"] for c in http.calls] == ["/secrets", f"/secrets/{SECRET_ID}"]


CREATE_WITH_SECRETS = {"image_name": "node", "secrets": {"API_KEY": "provider-key"}}


@pytest.mark.anyio
@pytest.mark.parametrize("async_client", [False, True])
@pytest.mark.parametrize("sandbox_id", ["", " "])
async def test_empty_sandbox_ids_are_unknown_outcomes(async_client, sandbox_id):
    manager, http = _sandbox_manager(
        {("POST", "/sandbox"): (200, dict(SANDBOX_DETAIL_PAYLOAD, id=sandbox_id))},
        async_client=async_client,
    )
    with pytest.raises(HyperbrowserError) as error:
        result = manager.create(CREATE_WITH_SECRETS)
        if async_client:
            await result
    assert error.value.code == "secret_process_outcome_unknown"
    assert error.value.retryable is False
    assert len(http.calls) == 1


@pytest.mark.parametrize(
    "outcome",
    [
        httpx.ReadTimeout("timed out"),
        httpx.RemoteProtocolError("connection closed"),
        httpx.Response(200, content=b"{", request=httpx.Request("POST", "https://x")),
        httpx.Response(
            502,
            content=b"<html>Bad gateway</html>",
            request=httpx.Request("POST", "https://x"),
        ),
        (200, {"unexpected": True}),
    ],
)
def test_a_create_with_secrets_that_may_have_arrived_has_an_unknown_outcome(outcome):
    manager, http = _sandbox_manager({("POST", "/sandbox"): outcome})

    with pytest.raises(HyperbrowserError) as error:
        manager.create(CREATE_WITH_SECRETS)

    assert error.value.code == "secret_process_outcome_unknown"
    assert error.value.retryable is False
    assert "could not confirm the create result" in str(error.value).lower()
    assert "list sandboxes before retrying" in str(error.value)
    assert len(http.calls) == 1


@pytest.mark.anyio
async def test_async_create_with_secrets_that_timed_out_has_an_unknown_outcome():
    manager, http = _sandbox_manager(
        {("POST", "/sandbox"): httpx.ReadTimeout("timed out")}, async_client=True
    )

    with pytest.raises(HyperbrowserError) as error:
        await manager.create(CREATE_WITH_SECRETS)

    assert error.value.code == "secret_process_outcome_unknown"
    assert error.value.retryable is False
    assert len(http.calls) == 1


@pytest.mark.parametrize("async_client", [False, True])
@pytest.mark.anyio
async def test_create_errors_keep_their_codes_when_the_outcome_is_known(async_client):
    rejected = (400, {"code": "SECRET_STARTUP_UNSUPPORTED", "message": "no cmd"})
    for params, outcome, code in [
        (CREATE_WITH_SECRETS, rejected, "SECRET_STARTUP_UNSUPPORTED"),
        (CREATE_WITH_SECRETS, httpx.ConnectError("refused"), None),
        ({"image_name": "node"}, httpx.ReadTimeout("timed out"), None),
    ]:
        manager, _ = _sandbox_manager({("POST", "/sandbox"): outcome}, async_client)
        with pytest.raises(HyperbrowserError) as error:
            result = manager.create(params)
            if async_client:
                await result
        assert error.value.code == code


@pytest.mark.parametrize("async_client", [False, True])
@pytest.mark.anyio
async def test_the_servers_unknown_process_outcome_uses_the_sdk_code(async_client):
    body = {
        "code": "SECRET_PROCESS_OUTCOME_UNKNOWN",
        "message": "The sandbox host did not confirm the process start",
        "retryable": False,
    }
    manager, http = _sandbox_manager(
        {("POST", "/sandbox/sbx_123/processes"): (502, body)}, async_client
    )

    with pytest.raises(HyperbrowserError) as error:
        result = manager.start_secret_process("sbx_123", {"command": "x"})
        if async_client:
            await result

    assert error.value.code == "secret_process_outcome_unknown"
    assert error.value.retryable is False
    assert error.value.status_code == 502
    assert error.value.details == dict(body, sandboxId="sbx_123")
    assert str(error.value).startswith(body["message"])
    assert len(http.calls) == 1


@pytest.mark.parametrize("async_client", [False, True])
@pytest.mark.anyio
async def test_a_started_process_may_report_its_id_as_process_id(async_client):
    process = dict(AGENT_PROCESS)
    process["processId"] = process.pop("id")
    manager, _ = _sandbox_manager(
        {
            ("POST", "/sandbox/sbx_123/processes"): (
                200,
                {"process": process, "secrets": RESOLVED},
            )
        },
        async_client,
    )
    sandbox = manager.attach(SandboxDetail(**SANDBOX_DETAIL_PAYLOAD))

    handle = sandbox.processes.start("node app.js", secrets={"API_KEY": "k"})
    if async_client:
        handle = await handle

    assert handle.id == "proc_9"
    assert handle.secrets[0].env == "API_KEY"


def test_the_processes_api_accepts_process_id_from_a_custom_start():
    process = dict(AGENT_PROCESS)
    process["processId"] = process.pop("id")
    api = SandboxProcessesApi(
        RuntimeScript(), lambda payload: {"process": process}, "sbx_123"
    )

    assert api.start("x", secrets={"API_KEY": "k"}).id == "proc_9"


def test_control_error_messages_name_the_sandbox_and_the_secret():
    with pytest.raises(HyperbrowserError) as error:
        ensure_response_ok(
            _error_response(
                502,
                {
                    "code": "SECRET_STARTUP_FAILED",
                    "message": "Stop it",
                    "sandboxId": "sbx_1",
                },
            ),
            "control",
        )
    assert error.value.args[0] == "Stop it (sandbox sbx_1)"
    assert error.value.details["sandboxId"] == "sbx_1"

    with pytest.raises(HyperbrowserError) as error:
        ensure_response_ok(
            _error_response(
                422,
                {
                    "code": "SECRET_DECRYPT_FAILED",
                    "message": "Could not open a secret",
                    "details": {"env": "API_KEY", "secretId": SECRET_ID, "version": 2},
                },
            ),
            "control",
        )
    assert error.value.args[0] == (
        f"Could not open a secret (API_KEY: secret {SECRET_ID}, version 2)"
    )

    # Context is only added to a message the body sent, and only for control.
    with pytest.raises(HyperbrowserError) as error:
        ensure_response_ok(_error_response(500, {"sandboxId": "sbx_1"}), "control")
    assert "sbx_1" not in error.value.args[0]
    with pytest.raises(HyperbrowserError) as error:
        ensure_response_ok(
            _error_response(500, {"message": "m", "sandboxId": "sbx_1"}), "runtime"
        )
    assert error.value.args[0] == "m"


@pytest.mark.parametrize("transport_type", ["sync", "async"])
@pytest.mark.anyio
async def test_transport_error_messages_name_the_sandbox(transport_type):
    from hyperbrowser.transport.async_transport import AsyncTransport
    from hyperbrowser.transport.sync import SyncTransport

    def respond(request):
        return httpx.Response(
            502, json={"code": "X_Y", "message": "failed", "sandboxId": "sbx_1"}
        )

    if transport_type == "sync":
        transport = SyncTransport("key")
        transport.client = httpx.Client(transport=httpx.MockTransport(respond))
        call = transport.post
    else:
        transport = AsyncTransport("key")
        transport.client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
        call = transport.post

    with pytest.raises(HyperbrowserError) as error:
        result = call("https://api.example.com/api/sandbox")
        if transport_type == "async":
            await result

    assert error.value.args[0] == "failed (sandbox sbx_1)"


def test_secrets_not_configured_is_not_retried():
    http = ScriptedHTTPClient(
        {
            ("GET", "/secrets/public-key"): (
                503,
                {"code": "SECRETS_NOT_CONFIGURED", "message": "Not configured"},
            )
        }
    )

    with pytest.raises(HyperbrowserError) as error:
        SecretManager(FakeClient(http)).get_public_key()

    assert error.value.code == "SECRETS_NOT_CONFIGURED"
    assert error.value.retryable is False
    assert len(http.calls) == 1


@pytest.mark.parametrize("transport_type", ["sync", "async"])
@pytest.mark.anyio
async def test_transport_does_not_retry_secrets_not_configured(transport_type):
    from hyperbrowser.transport.async_transport import AsyncTransport
    from hyperbrowser.transport.sync import SyncTransport

    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(
            503, json={"error": "SECRETS_NOT_CONFIGURED", "message": "Not configured"}
        )

    if transport_type == "sync":
        transport = SyncTransport("key")
        transport.client = httpx.Client(transport=httpx.MockTransport(respond))
    else:
        transport = AsyncTransport("key")
        transport.client = httpx.AsyncClient(transport=httpx.MockTransport(respond))

    with pytest.raises(HyperbrowserError) as error:
        result = transport.get("https://api.example.com/api/secrets/public-key")
        if transport_type == "async":
            await result

    assert error.value.retryable is False
    assert len(calls) == 1


@pytest.mark.parametrize("api_type", ["sync", "async"])
@pytest.mark.anyio
async def test_use_shell_is_rejected_for_starts_with_secrets(api_type):
    if api_type == "sync":
        api = SandboxProcessesApi(RuntimeScript(), lambda payload: {}, "sbx_123")
    else:
        api = AsyncSandboxProcessesApi(AsyncRuntimeScript(), None, "sbx_123")

    with pytest.raises(HyperbrowserError, match="use_shell") as error:
        result = api.start(
            {"command": "echo $API_KEY", "use_shell": True},
            secrets={"API_KEY": "provider-key"},
        )
        if api_type == "async":
            await result
    assert error.value.code == "secrets_unsupported"


def test_secret_names_env_names_and_versions_are_checked_locally():
    for name in ["", "-leading", "has space", "a" * 129, "name\n"]:
        with pytest.raises(ValueError, match="Invalid secret name"):
            CreateSecretParams(name=name)
    assert CreateSecretParams(name="a" * 128).name == "a" * 128

    for env in ["1ABC", "API-KEY", "", "__proto__", "KEY\n"]:
        with pytest.raises(ValueError, match="environment variable name"):
            SandboxExecParams(command="x", secrets={env: "provider-key"})
        with pytest.raises(ValueError, match="environment variable name"):
            CreateSandboxParams(image_name="node", secrets={env: "provider-key"})
    with pytest.raises(ValueError, match="Invalid secret name"):
        SandboxExecParams(command="x", secrets={"API_KEY": "bad name"})

    for version in [0, -1, 2**31, True, 1.0, "1"]:
        with pytest.raises(ValueError, match="Invalid secret version"):
            SandboxExecParams(
                command="x", secrets={"A": {"name": "k", "version": version}}
            )
    reference = SandboxExecParams(
        command="x", secrets={"A": {"name": "k", "version": 2**31 - 1}}
    ).secrets
    assert reference is not None and reference["A"].version == 2**31 - 1


def test_list_pages_and_version_numbers_are_checked_before_any_request():
    http = ScriptedHTTPClient({})
    manager = SecretManager(FakeClient(http))

    for params in [{"limit": 0}, {"limit": 101}, {"page": 0}]:
        with pytest.raises(ValueError):
            manager.list(params)
    for version in [0, 2**31, "1", True, 1.0, 1.5]:
        with pytest.raises(HyperbrowserError) as error:
            manager.delete_version("provider-key", version)
        assert error.value.code == "invalid_secret_version"
    assert http.calls == []


@pytest.mark.anyio
async def test_async_version_numbers_are_checked_before_any_request():
    http = AsyncScriptedHTTPClient({})
    manager = AsyncSecretManager(FakeClient(http))

    with pytest.raises(HyperbrowserError) as error:
        await manager.delete_version("provider-key", 0)
    assert error.value.code == "invalid_secret_version"
    with pytest.raises(ValueError):
        await manager.list({"limit": 101})
    assert http.calls == []


def test_secret_request_repr_does_not_expose_the_value():
    params = CreateSecretParams(name="key", value="dummy-sensitive-value")
    assert "dummy-sensitive-value" not in repr(params)
    assert "dummy-sensitive-value" not in str(params)
    assert "value" not in params.model_dump()
    assert params.value == "dummy-sensitive-value"


def test_secret_request_validation_message_does_not_expose_the_value():
    with pytest.raises(ValueError) as error:
        CreateSecretParams.model_validate({"value": "dummy-sensitive-value"})
    assert "dummy-sensitive-value" not in str(error.value)


@pytest.mark.parametrize(
    "model,params",
    [
        (CreateSandboxParams, {"image_name": "node"}),
        (SandboxExecParams, {"command": "x"}),
    ],
)
def test_secret_bindings_enforce_the_limit_and_omit_empty_maps(model, params):
    from hyperbrowser.client._request import dump_request

    assert "secrets" not in dump_request(dict(params, secrets={}), model)
    assert (
        len(model(**params, secrets={f"KEY_{i}": "k" for i in range(32)}).secrets) == 32
    )
    with pytest.raises(ValueError, match="32"):
        model(**params, secrets={f"KEY_{i}": "k" for i in range(33)})
