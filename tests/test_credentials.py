"""Typed secrets (totp, op_token), browser metadata, and credential fill."""

import asyncio
import json
import warnings

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
    SessionCredentialVault,
    UpdateSecretParams,
)
from hyperbrowser.secrets_common import check_totp_seed
from tests.test_secrets import (
    SECRET_ID,
    AsyncScriptedHTTPClient,
    FakeClient,
    ScriptedHTTPClient,
    _open,
    _public_key_payload,
    _secret,
)

TOTP_CONTEXT = f"hb-secret-v1:team_1:{SECRET_ID}:totp"
OP_TOKEN_CONTEXT = f"hb-secret-v1:team_1:{SECRET_ID}:op_token"
ORIGINS = ["https://github.com", "https://*.github.com"]
SEED = "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"


@pytest.fixture(scope="module")
def private_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=3072)


def _typed(secret_type, name="github-otp", origins=None, context=None):
    metadata = {"browser": {"allowedOrigins": origins}} if origins else {}
    return dict(
        _secret(name=name),
        type=secret_type,
        encryptionContext=context
        or {"totp": TOTP_CONTEXT, "op_token": OP_TOKEN_CONTEXT}.get(
            secret_type, _secret()["encryptionContext"]
        ),
        metadata=metadata,
    )


def _create_routes(private_key, created, upload=None):
    return {
        ("GET", "/secrets/public-key"): (200, _public_key_payload(private_key)),
        ("POST", "/secrets"): (201, created),
        ("POST", f"/secrets/{SECRET_ID}/versions"): upload
        or (201, {"version": 1, "kid": "k", "createdAt": "2026-10-01T00:00:00Z"}),
    }


def _assert_not_sent(calls, value):
    assert value not in json.dumps([call["json"] for call in calls])


# --- secret types and metadata ---


def test_secrets_default_to_plain_and_keep_unknown_metadata():
    plain = Secret.model_validate(_secret())
    assert plain.type == "secret"
    assert plain.metadata.browser is None

    for missing in [None, {}]:
        payload = dict(_secret(), type=None, metadata=missing)
        assert Secret.model_validate(payload).metadata.browser is None

    secret = Secret.model_validate(
        dict(
            _typed("totp"),
            metadata={
                "browser": {"allowedOrigins": ORIGINS, "future": 1},
                "other": {"x": True},
            },
        )
    )
    assert secret.type == "totp"
    assert secret.metadata.browser.allowed_origins == ORIGINS
    dumped = secret.metadata.model_dump(by_alias=True)
    assert dumped["other"] == {"x": True}
    assert dumped["browser"]["future"] == 1


def test_create_with_allowed_origins_makes_a_fillable_secret(private_key):
    created = _typed("secret", name="github-password", origins=ORIGINS)
    http = ScriptedHTTPClient(_create_routes(private_key, created))
    manager = SecretManager(FakeClient(http))

    secret = manager.create(
        {
            "name": "github-password",
            "value": "hunter2",
            "allowed_origins": ORIGINS,
            "description": "d",
        }
    )

    assert secret.latest_version == 1
    assert http.calls[1]["json"] == {
        "name": "github-password",
        "description": "d",
        "metadata": {"browser": {"allowedOrigins": ORIGINS}},
    }
    _, value = _open(private_key, http.calls[2]["json"]["envelope"])
    assert value == b"hunter2"
    _assert_not_sent(http.calls, "hunter2")

    # metadata.browser works too, but not together with allowed_origins.
    manager.create(
        CreateSecretParams(
            name="github-password",
            metadata=SecretMetadata.model_validate(
                {"browser": {"allowed_origins": ORIGINS}}
            ),
        )
    )
    assert http.calls[-1]["json"]["metadata"] == {
        "browser": {"allowedOrigins": ORIGINS}
    }
    http.calls.clear()
    with pytest.raises(ValueError, match="not both"):
        manager.create(
            {
                "name": "x",
                "allowed_origins": ORIGINS,
                "metadata": {"browser": {"allowed_origins": ORIGINS}},
            }
        )
    with pytest.raises(ValueError):
        manager.create({"name": "x", "allowed_origins": "https://github.com"})
    assert http.calls == []


def test_totp_secrets_seal_the_seed_under_the_returned_context(private_key):
    created = _typed("totp", origins=ORIGINS)
    http = ScriptedHTTPClient(_create_routes(private_key, created))
    manager = SecretManager(FakeClient(http))

    secret = manager.create(
        {
            "name": "github-otp",
            "type": "totp",
            "value": SEED.lower(),
            "allowed_origins": ORIGINS,
        }
    )

    assert secret.type == "totp"
    assert http.calls[1]["json"] == {
        "name": "github-otp",
        "type": "totp",
        "metadata": {"browser": {"allowedOrigins": ORIGINS}},
    }
    header, value = _open(private_key, http.calls[2]["json"]["envelope"])
    # The API's context, never one the SDK builds; the value is sent as given.
    assert header["ctx"] == TOTP_CONTEXT
    assert value == SEED.lower().encode()
    _assert_not_sent(http.calls, SEED.lower())


GOOD_SEEDS = [
    SEED,
    SEED.lower(),
    "jbsw y3dp ehpk 3pxp jbsw y3dp ehpk 3pxp",
    "JBSW-Y3DP-EHPK-3PXP-JBSW-Y3DP-EHPK-3PXP",
    "﻿" + SEED + "\n",
    "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PX=",
    f"otpauth://totp/GitHub:ada?secret={SEED}&issuer=GitHub",
    f"OTPAUTH://TOTP/x?secret={SEED}&algorithm=sha512&digits=8&period=300",
    f"otpauth://totp/x?secret={SEED}&algorithm=SHA256&digits=6&period=1",
]
BAD_SEEDS = [
    ("", "empty"),
    ("====", "empty"),
    ("not base32!", "not base32"),
    ("JBSWY3D1", "not base32"),
    (f"otpauth://hotp/x?secret={SEED}&counter=1", "HOTP"),
    (f"otpauth://steam/x?secret={SEED}", "otpauth://totp/"),
    (f"https://totp/x?secret={SEED}", "only otpauth://totp/"),
    ("otpauth://totp/x?issuer=GitHub", "no secret"),
    ("otpauth://totp/x?secret=", "no secret"),
    ("otpauth://totp/x?secret=0189", "not base32"),
    (f"otpauth://hotp/x?secret={SEED}", "HOTP"),
    (f"otpauth://totp/x?secret={SEED}&issuer=a\tb", "control characters"),
    (f"otpauth://totp/x?secret={SEED}\x7f", "control characters"),
    ("JBSW=Y3DP", "not base32"),
    ("JBSWY3DPE", "length"),
    ("JBSWY3DPEHP", "length"),
    ("JBSWY3DPEHPK3P", "length"),
    (f"otpauth://totp/x?secret={SEED}A", "length"),
    (f"otpauth://totp/x?secret={SEED}&algorithm=MD5", "algorithm"),
    (f"otpauth://totp/x?secret={SEED}&digits=7", "digits"),
    (f"otpauth://totp/x?secret={SEED}&digits=six", "digits"),
    (f"otpauth://totp/x?secret={SEED}&period=0", "period"),
    (f"otpauth://totp/x?secret={SEED}&period=301", "period"),
    (f"otpauth://totp/x?secret={SEED}&period=1_0", "period"),
]


@pytest.mark.parametrize("seed", GOOD_SEEDS)
def test_totp_seeds_the_platform_accepts_pass(seed):
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        check_totp_seed(seed)


@pytest.mark.parametrize("seed,reason", BAD_SEEDS)
def test_bad_totp_seeds_fail_before_any_request(seed, reason):
    http = ScriptedHTTPClient({})
    manager = SecretManager(FakeClient(http))

    with pytest.raises(HyperbrowserError) as error:
        manager.create({"name": "github-otp", "type": "totp", "value": seed})

    assert error.value.code == "invalid_secret_value"
    assert reason in str(error.value)
    if len(seed) > 4:
        assert seed not in str(error.value)
    assert http.calls == []


def test_short_totp_seeds_pass_without_warnings():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        check_totp_seed("JBSWY3DP")
        check_totp_seed("MY")


def test_op_tokens_take_any_string_but_never_allowed_origins(private_key):
    created = _typed("op_token", name="op-token")
    http = ScriptedHTTPClient(_create_routes(private_key, created))
    manager = SecretManager(FakeClient(http))

    # Tokens start with ops_, but other strings aren't refused.
    for token in ["ops_eyJzaWduSW5BZGRyZXNz", "not-a-prefix"]:
        manager.create({"name": "op-token", "type": "op_token", "value": token})
        header, value = _open(private_key, http.calls[-1]["json"]["envelope"])
        assert header["ctx"] == OP_TOKEN_CONTEXT and value == token.encode()

    http.calls.clear()
    for params in [
        {"name": "op-token", "type": "op_token", "allowed_origins": ORIGINS},
        {
            "name": "op-token",
            "type": "op_token",
            "metadata": {"browser": {"allowed_origins": ORIGINS}},
        },
    ]:
        with pytest.raises(ValueError, match="op_token"):
            manager.create(params)
    assert http.calls == []


def test_updates_refuse_allowed_origins_on_an_op_token():
    http = ScriptedHTTPClient(
        {
            ("GET", "/secrets"): (
                200,
                {"secrets": [_typed("op_token", name="op-token")], "totalCount": 1},
            )
        }
    )
    manager = SecretManager(FakeClient(http))

    with pytest.raises(HyperbrowserError) as error:
        manager.set_allowed_origins("op-token", ORIGINS)
    assert error.value.code == "invalid_secret_metadata"
    assert all(call["method"] == "GET" for call in http.calls)


def test_values_stay_out_of_reprs_and_dumps():
    params = CreateSecretParams(name="github-otp", type="totp", value=SEED)
    for text in [repr(params), str(params), json.dumps(params.model_dump())]:
        assert SEED not in text
    with pytest.raises(ValueError) as error:
        CreateSecretParams.model_validate({"value": SEED})
    assert SEED not in str(error.value)
    with pytest.raises(ValueError):
        CreateSecretParams(name="x", value={"username": "a"})  # type: ignore[arg-type]


# --- add_version ---


def test_add_version_checks_the_value_against_the_stored_type(private_key):
    versions_path = f"/secrets/{SECRET_ID}/versions"
    routes = {
        ("GET", "/secrets"): (200, {"secrets": [_typed("totp")], "totalCount": 1}),
        ("GET", "/secrets/public-key"): (200, _public_key_payload(private_key)),
        ("POST", versions_path): (201, {"version": 2, "kid": "k"}),
    }
    http = ScriptedHTTPClient(routes)
    manager = SecretManager(FakeClient(http))

    assert manager.add_version("github-otp", SEED).version == 2
    header, value = _open(private_key, http.calls[-1]["json"]["envelope"])
    assert header["ctx"] == TOTP_CONTEXT and value == SEED.encode()

    http.calls.clear()
    with pytest.raises(HyperbrowserError) as error:
        manager.add_version("github-otp", "hunter2!")
    assert error.value.code == "invalid_secret_value"
    assert [c["path"] for c in http.calls] == ["/secrets"]

    # A plain secret takes any value; common rules apply before the lookup.
    routes[("GET", "/secrets")] = (200, {"secrets": [_secret()], "totalCount": 1})
    manager.add_version("provider-key", "hunter2!")
    _, value = _open(private_key, http.calls[-1]["json"]["envelope"])
    assert value == b"hunter2!"
    http.calls.clear()
    for bad in ["", "a\x00b", {"username": "a"}]:
        with pytest.raises(HyperbrowserError):
            manager.add_version("provider-key", bad)  # type: ignore[arg-type]
    assert http.calls == []


# --- metadata updates and listing ---


def test_set_allowed_origins_replaces_or_clears_the_browser_metadata():
    http = ScriptedHTTPClient(
        {
            ("GET", "/secrets"): (200, {"secrets": [_typed("totp")], "totalCount": 1}),
            ("PATCH", f"/secrets/{SECRET_ID}"): (200, _typed("totp")),
        }
    )
    manager = SecretManager(FakeClient(http))

    manager.set_allowed_origins("github-otp", ("https://github.com",))
    assert http.calls[-1]["json"] == {
        "metadata": {"browser": {"allowedOrigins": ["https://github.com"]}}
    }

    manager.set_allowed_origins("github-otp", None)
    assert http.calls[-1]["json"] == {"metadata": {"browser": None}}
    assert json.dumps(http.calls[-1]["json"]) == '{"metadata": {"browser": null}}'

    for origins in ["https://github.com", [1]]:
        with pytest.raises(HyperbrowserError) as error:
            manager.set_allowed_origins("github-otp", origins)  # type: ignore[arg-type]
        assert error.value.code == "invalid_secret_metadata"


def test_update_sends_only_the_members_given():
    http = ScriptedHTTPClient(
        {
            ("GET", f"/secrets/{SECRET_ID}"): (200, dict(_typed("totp"), versions=[])),
            ("PATCH", f"/secrets/{SECRET_ID}"): (200, _typed("totp")),
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
        assert updated.type == "totp"

    http.calls.clear()
    with pytest.raises(ValueError):
        manager.update(SECRET_ID, {})
    assert http.calls == []


@pytest.mark.parametrize("secret_type", ["secret", "totp", "op_token"])
def test_list_filters_by_type(secret_type):
    http = ScriptedHTTPClient(
        {
            ("GET", "/secrets"): (
                200,
                {"secrets": [_typed(secret_type)], "totalCount": 1},
            )
        }
    )
    manager = SecretManager(FakeClient(http))

    listing = manager.list({"type": secret_type})

    assert http.calls[0]["params"] == {"type": secret_type}
    assert listing.secrets[0].type == secret_type
    with pytest.raises(ValueError):
        manager.list({"type": "credential"})  # type: ignore[typeddict-item]


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
        CreateSecretParams(name="provider-key", type="future_type")  # type: ignore[arg-type]


@pytest.mark.anyio
async def test_async_typed_secrets_round_trip(private_key):
    routes = _create_routes(private_key, _typed("totp", origins=ORIGINS))
    routes[("GET", "/secrets")] = (
        200,
        {"secrets": [_typed("totp", origins=ORIGINS)], "totalCount": 1},
    )
    routes[("PATCH", f"/secrets/{SECRET_ID}")] = (200, _typed("totp"))
    http = AsyncScriptedHTTPClient(routes)
    manager = AsyncSecretManager(FakeClient(http))

    secret = await manager.create(
        {
            "name": "github-otp",
            "type": "totp",
            "value": SEED,
            "allowed_origins": ORIGINS,
        }
    )
    assert secret.latest_version == 1
    assert http.calls[1]["json"]["metadata"] == {"browser": {"allowedOrigins": ORIGINS}}
    header, value = _open(private_key, http.calls[2]["json"]["envelope"])
    assert header["ctx"] == TOTP_CONTEXT and value == SEED.encode()

    await manager.add_version("github-otp", f"otpauth://totp/x?secret={SEED}")
    with pytest.raises(HyperbrowserError) as error:
        await manager.add_version("github-otp", "hunter2!")
    assert error.value.code == "invalid_secret_value"

    await manager.set_allowed_origins("github-otp", None)
    assert http.calls[-1]["json"] == {"metadata": {"browser": None}}
    _assert_not_sent(http.calls, SEED)

    http.calls.clear()
    with pytest.raises(HyperbrowserError):
        await manager.create({"name": "github-otp", "type": "totp", "value": "nope!"})
    assert http.calls == []
    assert (await manager.list({"type": "totp"})).secrets[0].type == "totp"


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
FIELDS = [
    {"field": "USERNAME", "selector": "#login_field"},
    {"field": "PASSWORD", "selector": "#password"},
    {"field": "OTP", "selector": "#app_totp"},
]
FILL_RESULT = {
    "pageId": "PAGE1",
    "origin": "https://github.com",
    "fields": [
        {
            "selector": "#login_field",
            "outcome": "filled",
            "secretId": SECRET_ID,
            "version": 1,
            "field": "USERNAME",
        },
        {
            "selector": "#password",
            "outcome": "not_accepted",
            "secretId": SECRET_ID,
            "version": 3,
            "field": "PASSWORD",
        },
        {
            "selector": "#app_totp",
            "outcome": "filled",
            "secretId": SECRET_ID,
            "version": 1,
            "field": "OTP",
            "expiresAt": "2026-10-14T12:00:30Z",
        },
    ],
}


def test_sessions_attach_secrets_and_vaults_at_creation(sdk):
    client, call, calls, outcomes = sdk
    attached = [{"id": SECRET_ID, "name": "github-password"}]
    respond(outcomes, dict(SESSION, credentials=attached))
    respond(outcomes, SESSION)
    respond(outcomes, SESSION)

    session = call(
        client.sessions.create,
        {
            "credentials": [
                "github-password",
                {"secret": "github-username"},
                {"vault": "github-login"},
            ]
        },
    )
    assert json.loads(calls[0].content)["credentials"] == [
        "github-password",
        {"secret": "github-username"},
        {"vault": "github-login"},
    ]
    assert session.credentials is not None
    assert [(c.id, c.name) for c in session.credentials] == [
        (SECRET_ID, "github-password")
    ]

    call(
        client.sessions.create,
        CreateSessionParams(credentials=[SessionCredentialVault(vault="github-login")]),
    )
    assert json.loads(calls[1].content)["credentials"] == [{"vault": "github-login"}]

    session = call(client.sessions.create, CreateSessionParams())
    assert "credentials" not in json.loads(calls[2].content)
    assert session.credentials is None


@pytest.mark.parametrize(
    "credentials",
    [
        ["bad name"],
        [{"vault": "a", "secret": "b"}],
        [{"vault": "-a"}],
        [{"login": "a"}],
        ["s"] * 21,
        "github",
    ],
)
def test_invalid_session_credentials_fail_before_http(sdk, credentials):
    client, call, calls, outcomes = sdk
    with pytest.raises(ValueError):
        call(client.sessions.create, {"credentials": credentials})
    assert not calls


def test_vault_fills_post_fields_and_parse_per_input_results(sdk):
    client, call, calls, outcomes = sdk
    respond(outcomes, FILL_RESULT)

    result = call(
        client.sessions.credentials.fill,
        "session /1",
        {
            "vault": "github-login",
            "fields": FIELDS,
            "page_url": "https://github.com/login",
            "frame_url": "https://github.com/",
        },
    )

    request = calls[0]
    assert request.method == "POST"
    assert request.url.raw_path == b"/api/session/session%20%2F1/credentials/fill"
    assert json.loads(request.content) == {
        "vault": "github-login",
        "fields": [{"selector": f["selector"], "field": f["field"]} for f in FIELDS],
        "pageUrl": "https://github.com/login",
        "frame": {"url": "https://github.com/"},
    }
    assert request.extensions["timeout"]["read"] == 30
    assert result.version is None
    assert result.page_id == "PAGE1"
    assert result.origin == "https://github.com"
    assert [(f.field, f.outcome, f.version) for f in result.fields] == [
        ("USERNAME", "filled", 1),
        ("PASSWORD", "not_accepted", 3),
        ("OTP", "filled", 1),
    ]
    assert result.fields[0].secret_id == SECRET_ID
    assert result.fields[0].expires_at is None
    assert result.fields[2].expires_at is not None
    assert result.fields[2].expires_at.isoformat() == "2026-10-14T12:00:30+00:00"


def test_single_secret_fills_report_the_version(sdk):
    client, call, calls, outcomes = sdk
    single = {
        "version": 3,
        "pageId": "PAGE1",
        "origin": "https://github.com",
        "fields": [
            {
                "selector": "#password",
                "outcome": "new",
                "secretId": SECRET_ID,
                "version": 3,
            }
        ],
    }
    respond(outcomes, single)

    client.timeout = 120
    result = call(
        client.sessions.credentials.fill,
        "s",
        FillCredentialParams(
            credential="github-password",
            fields=[{"selector": "#password"}],  # type: ignore[list-item]
            page_id="PAGE1",
        ),
    )
    assert json.loads(calls[0].content) == {
        "credential": "github-password",
        "fields": [{"selector": "#password"}],
        "pageId": "PAGE1",
    }
    assert calls[0].extensions["timeout"]["read"] == 120
    assert result.version == 3
    assert result.fields[0].field is None
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
    params = {"credential": "c", "fields": [{"selector": "#p"}]}

    with pytest.raises(HyperbrowserError) as raised:
        call(client.sessions.credentials.fill, "s", params)
    assert raised.value.code == "CREDENTIAL_PAGE_AMBIGUOUS"
    assert raised.value.status_code == 409
    assert raised.value.retryable is False
    assert raised.value.details["details"]["pages"] == pages

    with pytest.raises(HyperbrowserError) as raised:
        call(client.sessions.credentials.fill, "s", params)
    assert raised.value.code == "CREDENTIAL_FILL_TIMEOUT"
    assert raised.value.retryable is True
    # A fill is never retried automatically.
    assert len(calls) == 2


ONE = [{"selector": "#p"}]


@pytest.mark.parametrize(
    "params",
    [
        {"fields": ONE},
        {"credential": "c", "vault": "v", "fields": ONE},
        {"credential": "", "fields": ONE},
        {"credential": "c" * 256, "fields": ONE},
        {"credential": "c", "fields": [{"selector": "#p", "field": "PASSWORD"}]},
        {"vault": "v", "fields": ONE},
        {"vault": "bad name", "fields": [{"selector": "#p", "field": "P"}]},
        {"vault": "v", "fields": [{"selector": "#p", "field": "1PASSWORD"}]},
        {"vault": "v", "fields": [{"selector": "#p", "field": "__proto__"}]},
        {"credential": "c", "fields": []},
        {"credential": "c", "fields": [{"selector": f"#f{i}"} for i in range(17)]},
        {"credential": "c", "fields": [{"selector": "#p"}, {"selector": "#p"}]},
        {"credential": "c", "fields": [{"selector": " "}]},
        {"credential": "c", "fields": [{"selector": "é" * 513}]},
        {"credential": "c", "fields": [{}]},
        {"credential": "c", "fields": ONE, "page_id": "p", "page_url": "https://x"},
        {"credential": "c", "fields": ONE, "page_id": ""},
        {"credential": "c", "fields": ONE, "page_id": "p" * 129},
        {"credential": "c", "fields": ONE, "page_url": "u" * 2049},
        {"credential": "c", "fields": ONE, "frame_url": ""},
        {"credential": "c", "fields": ONE, "frame_url": "u" * 2049},
        {"credential": "c", "fields": ONE, "frame": {"url": "https://x"}},
        {"credential": "c"},
        {"credential": "c", "fields": "#p"},
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
    respond(outcomes, FILL_RESULT)
    call(
        client.sessions.credentials.fill,
        "s",
        {
            "vault": "v" * 128,
            "fields": [
                # 256-character entry names; 1024-byte selectors.
                {
                    "field": "F" * 256 if i == 0 else f"F{i}",
                    "selector": "é" * 511 + f"{i:02d}",
                }
                for i in range(16)
            ],
            "page_id": "p" * 128,
            "frame_url": "u" * 2048,
        },
    )
    call(
        client.sessions.credentials.fill,
        "s",
        {"credential": "c" * 255, "fields": ONE, "page_url": "u" * 2048},
    )
    assert len(calls) == 2
