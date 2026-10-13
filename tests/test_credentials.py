"""Credentials: typed secrets that browser sessions fill into pages."""

import asyncio
import json

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from hyperbrowser import AsyncHyperbrowser, Hyperbrowser
from hyperbrowser.client.managers.async_manager.secret import (
    SecretManager as AsyncSecretManager,
)
from hyperbrowser.client.managers.sync_manager.secret import SecretManager
from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.models import (
    CreateSecretParams,
    CreateSessionParams,
    FillCredentialParams,
    Secret,
    SecretMetadata,
    UpdateSecretParams,
)
from hyperbrowser.secrets_common import credential_value_bytes
from tests.test_secrets import (
    SECRET_ID,
    AsyncScriptedHTTPClient,
    FakeClient,
    ScriptedHTTPClient,
    _open,
    _public_key_payload,
    _secret,
)

CREDENTIAL_CONTEXT = f"hb-secret-v1:team_1:{SECRET_ID}:credential"
LOGIN = {"username": "ada@example.com", "password": "pässwörd-hunter2"}
ORIGINS = ["https://github.com", "https://*.github.com"]


@pytest.fixture(scope="module")
def private_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=3072)


def _credential(name="github", origins=None, latest=None):
    return dict(
        _secret(name=name, latest=latest),
        type="credential",
        encryptionContext=CREDENTIAL_CONTEXT,
        metadata={"browser": {"allowedOrigins": origins or ORIGINS}},
    )


def _create_routes(private_key, upload=None):
    return {
        ("GET", "/secrets/public-key"): (200, _public_key_payload(private_key)),
        ("POST", "/secrets"): (201, _credential()),
        ("POST", f"/secrets/{SECRET_ID}/versions"): upload
        or (201, {"version": 1, "kid": "k", "createdAt": "2026-10-01T00:00:00Z"}),
    }


def _assert_no_plaintext(calls):
    sent = json.dumps([call["json"] for call in calls], ensure_ascii=False)
    for value in LOGIN.values():
        assert value not in sent


# --- secret type and metadata ---


def test_secrets_default_to_plain_and_keep_unknown_metadata():
    plain = Secret.model_validate(_secret())
    assert plain.type == "secret"
    assert plain.metadata.browser is None

    for missing in [None, {}]:
        payload = dict(_secret(), type=None, metadata=missing)
        assert Secret.model_validate(payload).metadata.browser is None

    credential = Secret.model_validate(
        dict(
            _credential(),
            metadata={
                "browser": {"allowedOrigins": ORIGINS, "future": 1},
                "other": {"x": True},
            },
        )
    )
    assert credential.type == "credential"
    assert credential.metadata.browser.allowed_origins == ORIGINS
    dumped = credential.metadata.model_dump(by_alias=True)
    assert dumped["other"] == {"x": True}
    assert dumped["browser"]["future"] == 1


def test_credential_values_serialize_as_compact_utf8_json():
    assert credential_value_bytes({"username": "ada", "pass.word-1_": "é x"}) == (
        '{"username":"ada","pass.word-1_":"é x"}'.encode("utf-8")
    )
    assert credential_value_bytes({"a" * 64: "x"}) == b'{"' + b"a" * 64 + b'":"x"}'


# --- create_credential ---


def test_create_credential_uploads_json_bound_to_the_credential_context(private_key):
    http = ScriptedHTTPClient(_create_routes(private_key))
    manager = SecretManager(FakeClient(http))

    secret = manager.create_credential("github", LOGIN, ORIGINS, description="d")

    assert secret.type == "credential"
    assert secret.latest_version == 1
    assert secret.metadata.browser.allowed_origins == ORIGINS
    assert [c["path"] for c in http.calls] == [
        "/secrets/public-key",
        "/secrets",
        f"/secrets/{SECRET_ID}/versions",
    ]
    assert http.calls[1]["json"] == {
        "name": "github",
        "description": "d",
        "type": "credential",
        "metadata": {"browser": {"allowedOrigins": ORIGINS}},
    }
    upload = http.calls[2]["json"]
    assert set(upload) == {"envelope"}
    header, value = _open(private_key, upload["envelope"])
    assert header["ctx"] == CREDENTIAL_CONTEXT
    assert value == json.dumps(LOGIN, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )
    assert json.loads(value) == LOGIN
    _assert_no_plaintext(http.calls)


def test_create_accepts_a_credential_type_and_metadata(private_key):
    http = ScriptedHTTPClient(_create_routes(private_key))
    manager = SecretManager(FakeClient(http))

    manager.create(
        {
            "name": "github",
            "type": "credential",
            "metadata": {"browser": {"allowed_origins": ORIGINS}},
            "value": LOGIN,
        }
    )

    assert http.calls[1]["json"] == {
        "name": "github",
        "type": "credential",
        "metadata": {"browser": {"allowedOrigins": ORIGINS}},
    }
    _, value = _open(private_key, http.calls[2]["json"]["envelope"])
    assert json.loads(value) == LOGIN


def test_a_failed_credential_upload_reports_the_partial_create(private_key):
    http = ScriptedHTTPClient(
        _create_routes(
            private_key,
            upload=(409, {"code": "SECRET_KEY_OUTDATED", "message": "key rotated"}),
        )
    )
    manager = SecretManager(FakeClient(http))

    with pytest.raises(HyperbrowserError) as error:
        manager.create_credential("github", LOGIN, ORIGINS)

    assert error.value.code == "secret_value_not_stored"
    assert error.value.details == {"secretId": SECRET_ID, "name": "github"}
    assert error.value.cause.code == "SECRET_KEY_OUTDATED"


BAD_CREDENTIAL_VALUES = [
    {},
    {"bad key": "x"},
    {"": "x"},
    {"a" * 65: "x"},
    {"user/name": "x"},
    {1: "x"},
    {"username": ""},
    {"username": 1},
    {"username": None},
    {"username": "a\x00b"},
    {"username": "\ud800"},
    {"password": "x" * (32 * 1024)},
    "a plain string",
    b"plain bytes",
]


@pytest.mark.parametrize("value", BAD_CREDENTIAL_VALUES)
def test_bad_credential_values_fail_before_any_request(value):
    http = ScriptedHTTPClient({})
    manager = SecretManager(FakeClient(http))

    attempts = [
        lambda: manager.create_credential("github", value, ORIGINS),
        lambda: manager.create(
            {"name": "github", "type": "credential", "value": value}
        ),
    ]
    if isinstance(value, dict):
        # A str or bytes value is checked against the secret's type, which
        # takes a lookup; see the add_version tests.
        attempts.append(lambda: manager.add_version("github", value))
    for attempt in attempts:
        with pytest.raises(HyperbrowserError) as error:
            attempt()
        assert error.value.code == "invalid_secret_value"
        message = str(error.value)
        for item in value.values() if isinstance(value, dict) else [value]:
            if isinstance(item, str) and item:
                assert item not in message
    assert http.calls == []


def test_a_mapping_is_refused_for_a_plain_secret_before_any_request():
    http = ScriptedHTTPClient({})
    manager = SecretManager(FakeClient(http))

    for params in [
        {"name": "provider-key", "value": LOGIN},
        {"name": "provider-key", "type": "secret", "value": LOGIN},
    ]:
        with pytest.raises(HyperbrowserError) as error:
            manager.create(params)
        assert error.value.code == "invalid_secret_value"
        assert "credential" in str(error.value)
    assert http.calls == []


def test_credential_values_stay_out_of_reprs_and_dumps():
    params = CreateSecretParams(name="github", type="credential", value=LOGIN)
    for text in [repr(params), str(params), json.dumps(params.model_dump())]:
        assert LOGIN["password"] not in text
    with pytest.raises(ValueError) as error:
        CreateSecretParams.model_validate({"value": LOGIN})
    assert LOGIN["password"] not in str(error.value)


def test_allowed_origins_must_be_a_list():
    http = ScriptedHTTPClient({})
    manager = SecretManager(FakeClient(http))

    for origins in ["https://github.com", [1]]:
        with pytest.raises(HyperbrowserError) as error:
            manager.create_credential("github", LOGIN, origins)
        assert error.value.code == "invalid_secret_metadata"
        with pytest.raises(HyperbrowserError):
            manager.set_allowed_origins("github", origins)
    assert http.calls == []


# --- add_version ---


def test_add_version_checks_the_value_against_the_secrets_type(private_key):
    versions_path = f"/secrets/{SECRET_ID}/versions"
    routes = {
        ("GET", "/secrets"): (200, {"secrets": [_credential()], "totalCount": 1}),
        ("GET", "/secrets/public-key"): (200, _public_key_payload(private_key)),
        ("POST", versions_path): (201, {"version": 2, "kid": "k"}),
    }
    http = ScriptedHTTPClient(routes)
    manager = SecretManager(FakeClient(http))

    assert manager.add_version("github", LOGIN).version == 2
    header, value = _open(private_key, http.calls[-1]["json"]["envelope"])
    assert header["ctx"] == CREDENTIAL_CONTEXT
    assert json.loads(value) == LOGIN
    _assert_no_plaintext(http.calls)

    http.calls.clear()
    for value in ["plain", b"plain"]:
        with pytest.raises(HyperbrowserError) as error:
            manager.add_version("github", value)
        assert error.value.code == "invalid_secret_value"
    assert [c["path"] for c in http.calls] == ["/secrets", "/secrets"]

    routes[("GET", "/secrets")] = (200, {"secrets": [_secret()], "totalCount": 1})
    http.calls.clear()
    with pytest.raises(HyperbrowserError) as error:
        manager.add_version("provider-key", LOGIN)
    assert error.value.code == "invalid_secret_value"
    assert all(c["path"] != versions_path for c in http.calls)

    manager.add_version("provider-key", "plain")
    header, value = _open(private_key, http.calls[-1]["json"]["envelope"])
    assert header["ctx"] == _secret()["encryptionContext"] and value == b"plain"


# --- metadata updates and listing ---


def test_set_allowed_origins_replaces_or_clears_the_browser_metadata():
    http = ScriptedHTTPClient(
        {
            ("GET", "/secrets"): (200, {"secrets": [_credential()], "totalCount": 1}),
            ("PATCH", f"/secrets/{SECRET_ID}"): (200, _credential()),
        }
    )
    manager = SecretManager(FakeClient(http))

    manager.set_allowed_origins("github", ("https://github.com",))
    assert http.calls[-1]["json"] == {
        "metadata": {"browser": {"allowedOrigins": ["https://github.com"]}}
    }

    manager.set_allowed_origins("github", None)
    assert http.calls[-1]["json"] == {"metadata": {"browser": None}}
    assert json.dumps(http.calls[-1]["json"]) == '{"metadata": {"browser": null}}'


def test_update_sends_only_the_members_given():
    http = ScriptedHTTPClient(
        {
            ("GET", f"/secrets/{SECRET_ID}"): (200, dict(_credential(), versions=[])),
            ("PATCH", f"/secrets/{SECRET_ID}"): (200, _credential()),
        }
    )
    manager = SecretManager(FakeClient(http))

    for params, body in [
        ({"description": "d"}, {"description": "d"}),
        (UpdateSecretParams(description="d"), {"description": "d"}),
        ({"description": "d", "metadata": None}, {"description": "d"}),
        (
            {"metadata": {"browser": {"allowed_origins": ORIGINS}}},
            {"metadata": {"browser": {"allowedOrigins": ORIGINS}}},
        ),
        (
            UpdateSecretParams(metadata=SecretMetadata(browser=None)),
            {"metadata": {"browser": None}},
        ),
        ({"metadata": {"other": None}}, {"metadata": {"other": None}}),
    ]:
        updated = manager.update(SECRET_ID, params)
        assert http.calls[-1]["json"] == body
        assert updated.type == "credential"

    http.calls.clear()
    with pytest.raises(ValueError):
        manager.update(SECRET_ID, {})
    assert http.calls == []


def test_list_filters_by_type():
    http = ScriptedHTTPClient(
        {("GET", "/secrets"): (200, {"secrets": [_credential()], "totalCount": 1})}
    )
    manager = SecretManager(FakeClient(http))

    listing = manager.list({"type": "credential"})

    assert http.calls[0]["params"] == {"type": "credential"}
    assert listing.secrets[0].type == "credential"
    with pytest.raises(ValueError):
        manager.list({"type": "password"})


def test_secret_types_added_later_still_parse():
    future = dict(_secret(), type="future_type", metadata={"future": {"x": 1}})
    http = ScriptedHTTPClient(
        {
            ("GET", "/secrets"): (200, {"secrets": [future], "totalCount": 1}),
            ("GET", f"/secrets/{SECRET_ID}"): (200, dict(future, versions=[])),
        }
    )
    manager = SecretManager(FakeClient(http))

    assert manager.list().secrets[0].type == "future_type"
    assert manager.get(SECRET_ID).type == "future_type"
    assert manager.get("provider-key").type == "future_type"
    # Requests still only take the known types.
    with pytest.raises(ValueError):
        CreateSecretParams(name="provider-key", type="future_type")


@pytest.mark.anyio
async def test_async_secret_types_added_later_still_parse():
    future = dict(_secret(), type="future_type")
    http = AsyncScriptedHTTPClient(
        {
            ("GET", "/secrets"): (200, {"secrets": [future], "totalCount": 1}),
            ("GET", f"/secrets/{SECRET_ID}"): (200, dict(future, versions=[])),
        }
    )
    manager = AsyncSecretManager(FakeClient(http))

    assert (await manager.list()).secrets[0].type == "future_type"
    assert (await manager.get("provider-key")).type == "future_type"


@pytest.mark.anyio
async def test_async_credentials_round_trip(private_key):
    routes = _create_routes(private_key)
    routes[("GET", "/secrets")] = (200, {"secrets": [_credential()], "totalCount": 1})
    routes[("PATCH", f"/secrets/{SECRET_ID}")] = (200, _credential())
    http = AsyncScriptedHTTPClient(routes)
    manager = AsyncSecretManager(FakeClient(http))

    secret = await manager.create_credential("github", LOGIN, ORIGINS)
    assert secret.latest_version == 1
    assert http.calls[1]["json"]["metadata"] == {"browser": {"allowedOrigins": ORIGINS}}
    header, value = _open(private_key, http.calls[2]["json"]["envelope"])
    assert header["ctx"] == CREDENTIAL_CONTEXT and json.loads(value) == LOGIN

    await manager.add_version("github", LOGIN)
    _, value = _open(private_key, http.calls[-1]["json"]["envelope"])
    assert json.loads(value) == LOGIN
    with pytest.raises(HyperbrowserError) as error:
        await manager.add_version("github", "plain")
    assert error.value.code == "invalid_secret_value"

    await manager.set_allowed_origins("github", None)
    assert http.calls[-1]["json"] == {"metadata": {"browser": None}}
    _assert_no_plaintext(http.calls)

    http.calls.clear()
    with pytest.raises(HyperbrowserError):
        await manager.create_credential("github", {"username": ""}, ORIGINS)
    assert http.calls == []


# --- sessions ---


def mock_clients(is_async):
    """A client of either kind whose requests are answered from ``outcomes``."""
    loop = asyncio.new_event_loop()
    client = (AsyncHyperbrowser if is_async else Hyperbrowser)(api_key="test-key")
    calls = []
    outcomes = []

    def handler(req):
        calls.append(req)
        outcome = outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    def call(method, *args, **kwargs):
        result = method(*args, **kwargs)
        return loop.run_until_complete(result) if is_async else result

    call(client.transport.close)
    client.transport.client = (httpx.AsyncClient if is_async else httpx.Client)(
        transport=httpx.MockTransport(handler),
        headers={"x-api-key": "test-key"},
        timeout=30,
    )
    if is_async:
        client.transport._closed = False
    yield client, call, calls, outcomes
    call(client.close)
    loop.close()


@pytest.fixture(params=[False, True], ids=["sync", "async"])
def sdk(request):
    """Run the same checks through both public clients and transports."""
    yield from mock_clients(request.param)


def respond(outcomes, payload, status=200):
    outcomes.append(httpx.Response(status, json=payload))


SESSION = {
    "id": "session-1",
    "teamId": "team_1",
    "status": "active",
    "createdAt": "2026-10-01T00:00:00Z",
    "updatedAt": "2026-10-01T00:00:00Z",
    "sessionUrl": "https://app.hyperbrowser.ai/sessions/session-1",
    "proxyDataConsumed": "0",
    "liveUrl": "https://live",
    "token": "t",
}
FILL_RESULT = {
    "version": 3,
    "pageId": "PAGE1",
    "origin": "https://github.com",
    "fields": [
        {"field": "username", "outcome": "filled"},
        {"field": "password", "outcome": "not_accepted"},
    ],
}
FIELDS = [
    {"field": "username", "selector": "#login_field"},
    {"field": "password", "selector": "#password"},
]


def test_sessions_attach_credentials_at_creation(sdk):
    client, call, calls, outcomes = sdk
    respond(
        outcomes,
        dict(SESSION, credentials=[{"id": SECRET_ID, "name": "github"}]),
    )
    respond(outcomes, SESSION)

    session = call(client.sessions.create, {"credentials": ["github"]})
    assert json.loads(calls[0].content)["credentials"] == ["github"]
    assert session.credentials is not None
    assert [(c.id, c.name) for c in session.credentials] == [(SECRET_ID, "github")]

    session = call(client.sessions.create, CreateSessionParams())
    assert "credentials" not in json.loads(calls[1].content)
    assert session.credentials is None


def test_fill_posts_the_request_and_parses_outcomes(sdk):
    client, call, calls, outcomes = sdk
    respond(outcomes, FILL_RESULT)
    respond(outcomes, dict(FILL_RESULT, fields=[{"field": "otp", "outcome": "new"}]))

    result = call(
        client.sessions.credentials.fill,
        "session /1",
        {
            "credential": "github",
            "fields": FIELDS,
            "page_id": "PAGE1",
            "frame": {"url": "https://login.github.com/"},
        },
    )

    request = calls[0]
    assert request.method == "POST"
    assert request.url.raw_path == b"/api/session/session%20%2F1/credentials/fill"
    assert json.loads(request.content) == {
        "credential": "github",
        "fields": FIELDS,
        "pageId": "PAGE1",
        "frame": {"url": "https://login.github.com/"},
    }
    assert request.extensions["timeout"]["read"] == 30
    assert result.version == 3
    assert result.page_id == "PAGE1"
    assert result.origin == "https://github.com"
    assert [(f.field, f.outcome) for f in result.fields] == [
        ("username", "filled"),
        ("password", "not_accepted"),
    ]

    client.timeout = 120
    result = call(
        client.sessions.credentials.fill,
        "s",
        FillCredentialParams(credential="github", fields=FIELDS[:1]),
    )
    assert json.loads(calls[1].content) == {
        "credential": "github",
        "fields": FIELDS[:1],
    }
    assert calls[1].extensions["timeout"]["read"] == 120
    # Outcomes the SDK doesn't know yet still parse.
    assert result.fields[0].outcome == "new"


def test_fill_errors_keep_code_retryable_and_details(sdk):
    client, call, calls, outcomes = sdk
    pages = [
        {"pageId": "A", "url": "https://github.com/login", "title": "Sign in"},
        {"pageId": "B", "url": "https://github.com/", "title": "GitHub"},
    ]
    body = {
        "code": "CREDENTIAL_PAGE_AMBIGUOUS",
        "message": "Several pages could be filled",
        "details": {"pages": pages},
    }
    respond(outcomes, body, 409)
    respond(
        outcomes,
        {"code": "CREDENTIAL_FILL_TIMEOUT", "message": "timed out", "retryable": True},
        504,
    )

    with pytest.raises(HyperbrowserError) as raised:
        call(
            client.sessions.credentials.fill, "s", {"credential": "c", "fields": FIELDS}
        )
    assert raised.value.code == "CREDENTIAL_PAGE_AMBIGUOUS"
    assert raised.value.status_code == 409
    assert raised.value.retryable is False
    assert raised.value.details["details"]["pages"] == pages

    with pytest.raises(HyperbrowserError) as raised:
        call(
            client.sessions.credentials.fill, "s", {"credential": "c", "fields": FIELDS}
        )
    assert raised.value.code == "CREDENTIAL_FILL_TIMEOUT"
    assert raised.value.retryable is True
    # A fill is never retried automatically.
    assert len(calls) == 2


@pytest.mark.parametrize(
    "params",
    [
        {"credential": "github", "fields": []},
        {
            "credential": "github",
            "fields": [dict(FIELDS[0], field=f"f{i}") for i in range(17)],
        },
        {"credential": "github", "fields": [FIELDS[0], FIELDS[0]]},
        {"credential": "github", "fields": [{"field": "user name", "selector": "#u"}]},
        {"credential": "github", "fields": [{"field": "f" * 65, "selector": "#u"}]},
        {"credential": "github", "fields": [{"field": "username", "selector": " "}]},
        {"credential": "github", "fields": [{"field": "u", "selector": "é" * 513}]},
        {"credential": "github", "fields": [{"field": "username"}]},
        {"credential": "github", "fields": FIELDS, "page_id": ""},
        {"credential": "github", "fields": FIELDS, "page_id": "p" * 129},
        {"credential": "github", "fields": FIELDS, "frame": {"url": ""}},
        {"credential": "github", "fields": FIELDS, "frame": {"url": "u" * 2049}},
        {"credential": "", "fields": FIELDS},
        {"fields": FIELDS},
        {"credential": "github"},
        {"credential": "github", "fields": "username"},
        "github",
    ],
)
def test_invalid_fill_requests_fail_before_http(sdk, params):
    client, call, calls, outcomes = sdk
    with pytest.raises(HyperbrowserError) as raised:
        call(client.sessions.credentials.fill, "s", params)
    assert raised.value.code == "invalid_request"
    assert not calls


def test_fill_limits_are_inclusive(sdk):
    client, call, calls, outcomes = sdk
    respond(outcomes, FILL_RESULT)
    call(
        client.sessions.credentials.fill,
        "s",
        {
            "credential": "github",
            "fields": [
                {"field": f"f{i}" if i else "f" * 64, "selector": "é" * 512}
                for i in range(16)
            ],
            "page_id": "p" * 128,
            "frame": {"url": "u" * 2048},
        },
    )
    assert len(calls) == 1
