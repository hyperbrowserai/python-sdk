import base64
import json

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
    SandboxSnapshotSummary,
    StartSandboxFromSnapshotParams,
)
from hyperbrowser.sandbox_common import ensure_response_ok
from hyperbrowser.secrets_common import (
    SecretsSealer,
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

    def request_json(self, path, *, method="GET", json_body=None, **_):
        self.calls.append({"path": path, "method": method, "json": json_body})
        if path.endswith("/stdin"):
            if self.stdin is not None:
                raise self.stdin
            return {"success": True}
        if path.endswith("/wait"):
            step = self.waits.pop(0)
            if isinstance(step, BaseException):
                raise step
            return {"result": step}
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
