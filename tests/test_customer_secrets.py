"""Customer-protected secrets: customer keys, wrapped versions, unwrapping,
rewrapping, and passing unwrapped references to sandboxes and fills."""

import base64
import hashlib
import json
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed25519, rsa, x448, x25519

from hyperbrowser import AsyncHyperbrowser, create_customer_key, secret_envelope_digest
from hyperbrowser.client.managers.sandboxes.shared import (
    _normalize_exec_params,
    _secret_process_payload,
)
from hyperbrowser.client.managers.sync_manager.sandboxes.sandbox_processes import (
    SandboxProcessesApi,
)
from hyperbrowser.credentials_common import fill_credential_payload
from hyperbrowser.customer_key import CustomerKey
from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.models import (
    CreateSandboxParams,
    OnePasswordSource,
    SecretDetail,
    SecretReference,
    SessionDetail,
    VaultReference,
    WrappedSecretVersion,
)
from hyperbrowser.secrets_common import SecretsSealer
from tests.test_credentials import SESSION, mock_clients, respond
from tests.test_secrets import (
    AGENT_PROCESS,
    CONTEXT,
    SECRET_ID,
    RuntimeScript,
    _open,
    _public_key_payload,
)

VAULT_ID = "3f1d2c4b-5a6e-4f70-8a9b-0c1d2e3f4a5b"
FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "customer_key_interop.json").read_text()
)
UNWRAPPED = "eyJhbGciOiJSU0EtT0FFUC0yNTYifQ.key.iv.ciphertext.tag"


@pytest.fixture(scope="module")
def platform_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=3072)


@pytest.fixture(scope="module")
def rsa_key():
    return create_customer_key(rsa.generate_private_key(65537, 2048))


@pytest.fixture(scope="module")
def ec_key():
    return create_customer_key(ec.generate_private_key(ec.SECP256R1()))


@pytest.fixture(params=[False, True], ids=["sync", "async"])
def sdk(request):
    yield from mock_clients(request.param)


def _body(request):
    return json.loads(request.content)


def _header(envelope):
    segment = envelope.split(".")[0]
    return json.loads(base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4)))


def _secret(protection="customer", **overrides):
    return dict(
        {
            "id": SECRET_ID,
            "name": "db-password",
            "description": "",
            "type": "secret",
            "metadata": {},
            "protection": protection,
            "encryptionContext": CONTEXT,
            "latestVersion": None,
            "createdAt": "2026-11-01T00:00:00Z",
            "updatedAt": "2026-11-01T00:00:00Z",
        },
        **overrides,
    )


def _stored(platform_key, key, value="hunter2", version=1):
    """A stored customer-protected version: ``value`` sealed to the platform
    and wrapped with ``key``."""
    sealer = SecretsSealer(_public_key_payload(platform_key))
    inner = sealer.seal(CONTEXT, value)
    return inner, {
        "version": version,
        "kid": sealer.kid,
        "retiresAt": None,
        "outerKid": key.kid,
        "innerDigest": secret_envelope_digest(inner),
        "envelope": key.wrap(inner, CONTEXT),
    }


# --- customer keys ---


@pytest.mark.parametrize(
    "generate, algorithm, expected_alg",
    [
        (lambda: rsa.generate_private_key(65537, 2048), None, "RSA-OAEP-256"),
        (lambda: ec.generate_private_key(ec.SECP384R1()), None, "ECDH-ES+A256KW"),
        (lambda: ec.generate_private_key(ec.SECP521R1()), "ECDH-ES", "ECDH-ES"),
        (x25519.X25519PrivateKey.generate, None, "ECDH-ES+A256KW"),
        (x448.X448PrivateKey.generate, "ECDH-ES", "ECDH-ES"),
    ],
    ids=["rsa", "p-384", "p-521", "x25519", "x448"],
)
def test_keys_wrap_to_the_secrets_context_and_unwrap(generate, algorithm, expected_alg):
    key = create_customer_key(generate(), algorithm=algorithm)
    assert isinstance(key, CustomerKey)
    wrapped = key.wrap("a.b.c.d.e", CONTEXT)
    header = _header(wrapped)
    assert header["alg"] == expected_alg
    assert (header["enc"], header["kid"], header["ctx"]) == (
        "A256GCM",
        key.kid,
        CONTEXT,
    )
    assert set(header) == (
        {"alg", "enc", "kid", "ctx"}
        if expected_alg == "RSA-OAEP-256"
        else {"alg", "enc", "kid", "ctx", "epk"}
    )
    if expected_alg == "ECDH-ES":
        assert wrapped.split(".")[1] == ""
    assert key.unwrap(wrapped) == "a.b.c.d.e"


def test_the_kid_is_the_rfc_7638_thumbprint_unless_named():
    private_key = ec.generate_private_key(ec.SECP256R1())
    numbers = private_key.public_key().public_numbers()

    def b64(value):
        return base64.urlsafe_b64encode(value.to_bytes(32, "big")).rstrip(b"=").decode()

    members = '{"crv":"P-256","kty":"EC","x":"%s","y":"%s"}' % (
        b64(numbers.x),
        b64(numbers.y),
    )
    thumbprint = (
        base64.urlsafe_b64encode(hashlib.sha256(members.encode()).digest())
        .rstrip(b"=")
        .decode()
    )
    pem = private_key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    assert create_customer_key(private_key).kid == thumbprint
    assert create_customer_key(private_key.public_key()).kid == thumbprint
    assert create_customer_key(pem).kid == thumbprint
    assert create_customer_key(pem.decode()).kid == thumbprint
    assert create_customer_key(private_key, kid="kms/key-1").kid == "kms/key-1"
    jwk = {"kty": "EC", "crv": "P-256", "x": b64(numbers.x), "y": b64(numbers.y)}
    assert create_customer_key(jwk).kid == thumbprint
    assert create_customer_key(dict(jwk, kid="team-key")).kid == "team-key"


def test_public_keys_wrap_and_private_keys_unwrap():
    private_key = rsa.generate_private_key(65537, 2048)
    der = private_key.private_bytes(
        serialization.Encoding.DER,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    public_only = create_customer_key(private_key.public_key())
    from_der = create_customer_key(der)
    assert from_der.can_unwrap and not public_only.can_unwrap
    wrapped = public_only.wrap("a.b.c.d.e", CONTEXT)
    assert from_der.unwrap(wrapped) == "a.b.c.d.e"
    with pytest.raises(HyperbrowserError) as error:
        public_only.unwrap(wrapped)
    assert error.value.code == "customer_key_private_key_required"


@pytest.mark.parametrize(
    "key, options, message",
    [
        (lambda: rsa.generate_private_key(65537, 1024), {}, "at least 2048 bits"),
        (lambda: ec.generate_private_key(ec.SECP256K1()), {}, "P-256, P-384 or P-521"),
        (ed25519.Ed25519PrivateKey.generate, {}, "must be RSA"),
        (lambda: "not a key", {}, "not a PEM or DER key"),
        (lambda: {"kty": "oct", "k": "AAAA"}, {}, "must be RSA"),
        (
            lambda: rsa.generate_private_key(65537, 2048),
            {"algorithm": "ECDH-ES"},
            "RSA-OAEP-256",
        ),
        (
            x25519.X25519PrivateKey.generate,
            {"algorithm": "RSA-OAEP-256"},
            "ECDH-ES",
        ),
        (x25519.X25519PrivateKey.generate, {"kid": "caf\u00e9"}, "printable ASCII"),
        (x25519.X25519PrivateKey.generate, {"kid": "x" * 257}, "1-256"),
    ],
)
def test_keys_the_api_would_refuse_are_rejected(key, options, message):
    with pytest.raises(HyperbrowserError, match=message) as error:
        create_customer_key(key(), **options)
    assert error.value.code == "invalid_customer_key"


def test_unwrap_names_a_key_mismatch_and_refuses_tampering(rsa_key, ec_key):
    wrapped = rsa_key.wrap("a.b.c.d.e", CONTEXT)
    with pytest.raises(HyperbrowserError) as error:
        ec_key.unwrap(wrapped)
    assert error.value.code == "customer_key_mismatch"

    segments = wrapped.split(".")
    tag = bytearray(base64.urlsafe_b64decode(segments[4] + "=="))
    tag[0] ^= 1
    segments[4] = base64.urlsafe_b64encode(bytes(tag)).rstrip(b"=").decode()
    with pytest.raises(HyperbrowserError) as error:
        rsa_key.unwrap(".".join(segments))
    assert error.value.code == "customer_key_unwrap_failed"
    with pytest.raises(HyperbrowserError, match="five segments"):
        rsa_key.unwrap("a.b.c")


@pytest.mark.parametrize("item", FIXTURE["keys"], ids=lambda item: item["label"])
def test_envelopes_wrapped_by_either_sdk_unwrap(item):
    key = create_customer_key(item["jwk"], algorithm=item["algorithm"])
    assert key.kid == item["kid"]
    for wrapped in (item["wrappedByNode"], item["wrappedByPython"]):
        assert _header(wrapped)["ctx"] == FIXTURE["context"]
        assert key.unwrap(wrapped) == FIXTURE["inner"]
    assert secret_envelope_digest(FIXTURE["inner"]) == FIXTURE["innerDigest"]


# --- secrets ---


def test_create_wraps_the_first_value_with_the_customer_key(sdk, platform_key, rsa_key):
    client, call, calls, outcomes = sdk
    respond(outcomes, _public_key_payload(platform_key))
    respond(outcomes, _secret(), 201)
    respond(outcomes, {"version": 1, "kid": "p", "outerKid": rsa_key.kid}, 201)

    created = call(
        client.secrets.create,
        {"name": "db-password", "value": "hunter2", "customer_key": rsa_key},
    )

    assert created.protection == "customer" and created.latest_version == 1
    assert [(c.method, c.url.path) for c in calls] == [
        ("GET", "/api/secrets/public-key"),
        ("POST", "/api/secrets"),
        ("POST", f"/api/secrets/{SECRET_ID}/versions"),
    ]
    assert _body(calls[1]) == {"name": "db-password", "protection": "customer"}
    upload = _body(calls[2])
    assert set(upload) == {"envelope", "innerDigest", "innerKid"}
    assert _header(upload["envelope"])["ctx"] == CONTEXT
    inner = rsa_key.unwrap(upload["envelope"])
    assert secret_envelope_digest(inner) == upload["innerDigest"]
    header, value = _open(platform_key, inner)
    assert (header["kid"], value) == (upload["innerKid"], b"hunter2")


def test_create_checks_protection_before_any_request(sdk, rsa_key):
    client, call, calls, outcomes = sdk
    respond(outcomes, _secret(), 201)
    call(client.secrets.create, {"name": "db-password", "protection": "customer"})
    assert _body(calls[0]) == {"name": "db-password", "protection": "customer"}

    for params in [
        {"name": "db-password", "protection": "customer", "value": "v"},
        {"name": "db-password", "protection": "platform", "customer_key": rsa_key},
        {"name": "db-password", "customer_key": object()},
    ]:
        with pytest.raises(HyperbrowserError) as error:
            call(client.secrets.create, params)
        assert error.value.code == "invalid_request"
    assert len(calls) == 1


def test_add_version_wraps_and_matches_the_secrets_protection(
    sdk, platform_key, ec_key
):
    client, call, calls, outcomes = sdk
    respond(outcomes, dict(_secret(), versions=[]))
    respond(outcomes, _public_key_payload(platform_key))
    respond(outcomes, {"version": 2, "kid": "p", "outerKid": ec_key.kid}, 201)
    version = call(client.secrets.add_version, SECRET_ID, "v2", customer_key=ec_key)
    assert version.outer_kid == ec_key.kid
    upload = _body(calls[-1])
    assert _open(platform_key, ec_key.unwrap(upload["envelope"]))[1] == b"v2"

    respond(outcomes, dict(_secret(), versions=[]))
    with pytest.raises(HyperbrowserError, match="pass customer_key"):
        call(client.secrets.add_version, SECRET_ID, "v3")
    respond(outcomes, dict(_secret("platform"), versions=[]))
    with pytest.raises(HyperbrowserError, match="omit customer_key"):
        call(client.secrets.add_version, SECRET_ID, "v3", customer_key=ec_key)
    assert [c.method for c in calls].count("POST") == 1


def test_unwrap_returns_a_pinned_reference_checked_against_the_digest(
    sdk, platform_key, rsa_key, ec_key
):
    client, call, calls, outcomes = sdk
    inner, stored = _stored(platform_key, rsa_key, version=4)
    respond(outcomes, dict(_secret(latestVersion=4), versions=[]))
    respond(outcomes, stored)

    reference = call(client.secrets.unwrap, SECRET_ID, [ec_key, rsa_key])

    assert isinstance(reference, SecretReference)
    assert (reference.name, reference.version, reference.unwrapped) == (
        "db-password",
        4,
        inner,
    )
    assert "unwrapped" not in repr(reference)
    assert calls[1].url.path == f"/api/secrets/{SECRET_ID}/versions/latest/wrapped"

    respond(outcomes, dict(_secret(), versions=[]))
    respond(outcomes, stored)
    call(client.secrets.unwrap, SECRET_ID, rsa_key, version=4)
    assert calls[-1].url.path == f"/api/secrets/{SECRET_ID}/versions/4/wrapped"

    respond(outcomes, dict(_secret(), versions=[]))
    respond(outcomes, stored)
    with pytest.raises(HyperbrowserError) as error:
        call(client.secrets.unwrap, SECRET_ID, ec_key)
    assert error.value.code == "customer_key_mismatch"

    respond(outcomes, dict(_secret(), versions=[]))
    respond(outcomes, dict(stored, innerDigest=secret_envelope_digest("other")))
    with pytest.raises(HyperbrowserError, match="doesn't match its innerDigest"):
        call(client.secrets.unwrap, SECRET_ID, rsa_key)

    count = len(calls)
    with pytest.raises(HyperbrowserError, match="at least one customer key"):
        call(client.secrets.unwrap, SECRET_ID, [])
    with pytest.raises(HyperbrowserError, match="Invalid secret version"):
        call(client.secrets.unwrap, SECRET_ID, rsa_key, version=0)
    assert len(calls) == count


def test_get_wrapped_version_returns_the_outer_envelope(sdk, platform_key, rsa_key):
    client, call, calls, outcomes = sdk
    _, stored = _stored(platform_key, rsa_key, version=2)
    respond(outcomes, dict(_secret(), versions=[]))
    respond(outcomes, stored)
    wrapped = call(client.secrets.get_wrapped_version, SECRET_ID, 2)
    assert isinstance(wrapped, WrappedSecretVersion)
    assert (wrapped.outer_kid, wrapped.inner_digest) == (
        rsa_key.kid,
        stored["innerDigest"],
    )
    assert calls[-1].url.path == f"/api/secrets/{SECRET_ID}/versions/2/wrapped"


def test_rewrap_moves_versions_to_the_new_key_and_keeps_the_inner_envelope(
    sdk, platform_key, rsa_key, ec_key
):
    client, call, calls, outcomes = sdk
    inner_2, v2 = _stored(platform_key, rsa_key, "two", 2)
    inner_1, v1 = _stored(platform_key, rsa_key, "one", 1)
    _, v3 = _stored(platform_key, ec_key, "three", 3)
    versions = [
        {key: item[key] for key in ("version", "kid", "outerKid")}
        for item in (v3, v2, v1)
    ]
    respond(outcomes, dict(_secret(latestVersion=3), versions=versions))
    respond(outcomes, v2)
    respond(outcomes, dict(v2, outerKid=ec_key.kid))
    respond(outcomes, v1)
    respond(outcomes, dict(v1, outerKid=ec_key.kid))

    rewrapped = call(client.secrets.rewrap, SECRET_ID, from_key=rsa_key, to_key=ec_key)

    assert [(c.method, c.url.path) for c in calls[1:]] == [
        ("GET", f"/api/secrets/{SECRET_ID}/versions/2/wrapped"),
        ("PUT", f"/api/secrets/{SECRET_ID}/versions/2/wrapping"),
        ("GET", f"/api/secrets/{SECRET_ID}/versions/1/wrapped"),
        ("PUT", f"/api/secrets/{SECRET_ID}/versions/1/wrapping"),
    ]
    assert [(item.version, item.outer_kid) for item in rewrapped] == [
        (2, ec_key.kid),
        (1, ec_key.kid),
    ]
    for request, inner, stored in ((calls[2], inner_2, v2), (calls[4], inner_1, v1)):
        body = _body(request)
        assert body["innerDigest"] == stored["innerDigest"]
        assert _header(body["envelope"])["kid"] == ec_key.kid
        assert ec_key.unwrap(body["envelope"]) == inner


def test_rewrap_refuses_platform_secrets_and_replace_wrapping_sends_as_given(
    sdk, rsa_key, ec_key
):
    client, call, calls, outcomes = sdk
    respond(outcomes, dict(_secret("platform"), versions=[]))
    with pytest.raises(HyperbrowserError, match="not customer-protected"):
        call(client.secrets.rewrap, SECRET_ID, from_key=rsa_key, to_key=ec_key)

    respond(outcomes, dict(_secret(), versions=[]))
    respond(
        outcomes,
        {
            "version": 5,
            "kid": "p",
            "outerKid": "k",
            "innerDigest": "d",
            "envelope": "e",
        },
    )
    call(
        client.secrets.replace_version_wrapping,
        SECRET_ID,
        5,
        {"envelope": "outer", "inner_digest": "digest"},
    )
    assert calls[-1].method == "PUT"
    assert _body(calls[-1]) == {"envelope": "outer", "innerDigest": "digest"}


def test_versions_report_outer_kid_and_retires_at():
    detail = SecretDetail.model_validate(
        dict(
            _secret(),
            versions=[
                {
                    "version": 2,
                    "kid": "p",
                    "outerKid": "k",
                    "retiresAt": "2027-01-01T00:00:00Z",
                }
            ],
        )
    )
    assert detail.versions[0].outer_kid == "k"
    assert detail.versions[0].retires_at is not None
    assert SecretDetail.model_validate(dict(_secret(), protection=None)).protection == (
        "platform"
    )


def test_the_async_client_awaits_customer_keys_and_the_sync_one_refuses_them(
    platform_key, rsa_key
):
    class KmsKey:
        kid = rsa_key.kid

        async def wrap(self, inner_envelope, encryption_context):
            return rsa_key.wrap(inner_envelope, encryption_context)

        async def unwrap(self, wrapped_envelope):
            return rsa_key.unwrap(wrapped_envelope)

    inner, stored = _stored(platform_key, rsa_key, version=3)
    for is_async in (True, False):
        clients = mock_clients(is_async)
        client, call, _, outcomes = next(clients)
        respond(outcomes, dict(_secret(), versions=[]))
        respond(outcomes, stored)
        if is_async:
            assert isinstance(client, AsyncHyperbrowser)
            assert call(client.secrets.unwrap, SECRET_ID, KmsKey()).unwrapped == inner
        else:
            with pytest.raises(HyperbrowserError, match="use the async client"):
                call(client.secrets.unwrap, SECRET_ID, KmsKey())
        clients.close()


# --- vaults ---


def _vault():
    return {
        "id": VAULT_ID,
        "name": "app-env",
        "description": "",
        "entries": {
            "DB_PASSWORD": {
                "name": "db-password",
                "secretId": SECRET_ID,
                "version": None,
                "protection": "customer",
            },
        },
        "createdAt": "2026-11-01T00:00:00Z",
        "updatedAt": "2026-11-01T00:00:00Z",
    }


def test_vault_unwrap_returns_the_reference_sandboxes_take(
    sdk, platform_key, rsa_key, ec_key
):
    client, call, calls, outcomes = sdk
    inner, stored = _stored(platform_key, ec_key, version=7)
    wrapped_vault = {
        "id": VAULT_ID,
        "name": "app-env",
        "entries": {
            "DB_PASSWORD": dict(stored, name="db-password", secretId=SECRET_ID)
        },
    }
    respond(outcomes, _vault())
    respond(outcomes, wrapped_vault)

    reference = call(client.vaults.unwrap, VAULT_ID, [rsa_key, ec_key])

    assert isinstance(reference, VaultReference)
    assert reference.model_dump() == {
        "name": "app-env",
        "unwrapped": {"DB_PASSWORD": {"version": 7, "unwrapped": inner}},
    }
    assert [c.url.path for c in calls] == [
        f"/api/vaults/{VAULT_ID}",
        f"/api/vaults/{VAULT_ID}/wrapped",
    ]

    respond(outcomes, _vault())
    respond(outcomes, wrapped_vault)
    with pytest.raises(
        HyperbrowserError, match="Entry DB_PASSWORD of vault app-env"
    ) as error:
        call(client.vaults.unwrap, VAULT_ID, rsa_key)
    assert error.value.code == "customer_key_mismatch"


def test_vault_entries_report_their_protection(sdk):
    client, call, calls, outcomes = sdk
    respond(outcomes, _vault())
    vault = call(client.vaults.get, VAULT_ID)
    assert vault.entries["DB_PASSWORD"].protection == "customer"


# --- uses ---


def test_unwrapped_references_must_pin_a_version():
    assert SecretReference(name="db", version=3, unwrapped=UNWRAPPED).version == 3
    for params in [
        {"name": "db", "unwrapped": UNWRAPPED},
        {"name": "db", "version": "latest", "unwrapped": UNWRAPPED},
        {"name": "db", "version": 1, "unwrapped": ""},
        {"name": "db", "version": 1, "unwrapped": "x" * (64 * 1024 + 1)},
    ]:
        with pytest.raises(ValueError):
            SecretReference.model_validate(params)


def test_sandbox_create_sends_unwrapped_references():
    params = CreateSandboxParams(
        image_name="node",
        secrets={
            "API_KEY": {"name": "provider-key", "version": 4, "unwrapped": UNWRAPPED}
        },
        vault={
            "name": "app-env",
            "unwrapped": {"DB": {"version": 7, "unwrapped": UNWRAPPED}},
        },
        one_password={
            "token": {"name": "op-token", "version": 2, "unwrapped": UNWRAPPED},
            "vault": "Engineering",
            "fields": {"DB_PASS": {"item": "Postgres", "field": "password"}},
        },
    )
    assert params.model_dump(by_alias=True, exclude_none=True) == {
        "imageName": "node",
        "secrets": {
            "API_KEY": {"name": "provider-key", "version": 4, "unwrapped": UNWRAPPED}
        },
        "vault": {
            "name": "app-env",
            "unwrapped": {"DB": {"version": 7, "unwrapped": UNWRAPPED}},
        },
        "onePassword": {
            "token": {"name": "op-token", "version": 2, "unwrapped": UNWRAPPED},
            "vault": "Engineering",
            "fields": {"DB_PASS": {"item": "Postgres", "field": "password"}},
        },
    }


@pytest.mark.parametrize(
    "vault, message",
    [
        ({"name": "app env", "unwrapped": {}}, "Invalid secret name"),
        ({"name": "app-env"}, "unwrapped"),
        (
            {"name": "app-env", "unwrapped": {"1A": {"version": 1, "unwrapped": "e"}}},
            "1A",
        ),
        (
            {
                "name": "app-env",
                "unwrapped": {"A": {"version": "latest", "unwrapped": "e"}},
            },
            "version",
        ),
        ({"name": "app-env", "unwrapped": {"A": {"version": 1}}}, "unwrapped"),
        (
            {
                "name": "app-env",
                "unwrapped": {"A": {"version": 1, "unwrapped": "e", "x": 1}},
            },
            "x",
        ),
        (
            {
                "name": "app-env",
                "unwrapped": {
                    f"E{i}": {"version": 1, "unwrapped": "e"} for i in range(33)
                },
            },
            "At most 32",
        ),
    ],
)
def test_bad_vault_references_are_refused_locally(vault, message):
    with pytest.raises(ValueError, match=message):
        CreateSandboxParams(image_name="node", vault=vault)


def test_processes_send_vault_references_and_unwrapped_tokens():
    reference = VaultReference(
        name="app-env", unwrapped={"DB": {"version": 7, "unwrapped": UNWRAPPED}}
    )
    token = SecretReference(name="op-token", version=2, unwrapped=UNWRAPPED)
    payload = _secret_process_payload(
        _normalize_exec_params(
            "node app.js",
            vault=reference,
            one_password=OnePasswordSource(token=token, vault="Eng", fields={}),
        )
    )
    assert payload == {
        "command": "node app.js",
        "vault": {
            "name": "app-env",
            "unwrapped": {"DB": {"version": 7, "unwrapped": UNWRAPPED}},
        },
        "onePassword": {
            "token": {"name": "op-token", "version": 2, "unwrapped": UNWRAPPED},
            "vault": "Eng",
            "fields": {},
        },
    }

    starts = []

    def start(body):
        starts.append(body)
        return {"process": AGENT_PROCESS, "secrets": []}

    api = SandboxProcessesApi(RuntimeScript(), start, "sbx_123")
    api.start(
        "node app.js",
        secrets={"API_KEY": {"name": "k", "version": 1, "unwrapped": UNWRAPPED}},
        vault={"name": "app-env", "unwrapped": {}},
    )
    assert starts[-1] == {
        "command": "node app.js",
        "secrets": {"API_KEY": {"name": "k", "version": 1, "unwrapped": UNWRAPPED}},
        "vault": {"name": "app-env", "unwrapped": {}},
    }


def test_fills_send_an_unwrapped_op_token():
    body = fill_credential_payload(
        {
            "one_password": {
                "token": {"name": "op-token", "version": 2, "unwrapped": UNWRAPPED},
                "vault": "Eng",
                "allowed_origins": ["https://example.com"],
            },
            "fields": [{"selector": "#p", "ref": {"item": "i", "field": "f"}}],
        }
    )
    assert body["onePassword"]["token"] == {
        "name": "op-token",
        "version": 2,
        "unwrapped": UNWRAPPED,
    }
    with pytest.raises(HyperbrowserError, match="Pin the version"):
        fill_credential_payload(
            {
                "one_password": {
                    "token": {"name": "op-token", "unwrapped": UNWRAPPED},
                    "vault": "Eng",
                    "allowed_origins": ["https://example.com"],
                },
                "fields": [{"selector": "#p", "ref": {"item": "i", "field": "f"}}],
            }
        )


def test_sessions_list_the_vaults_attached_by_reference(sdk):
    client, call, calls, outcomes = sdk
    vaults = [{"id": VAULT_ID, "name": "app-env"}]
    respond(outcomes, dict(SESSION, vaults=vaults))
    session = call(client.sessions.create, {"credentials": [{"vault": "app-env"}]})
    assert isinstance(session, SessionDetail)
    assert [(v.id, v.name) for v in session.vaults or []] == [(VAULT_ID, "app-env")]
