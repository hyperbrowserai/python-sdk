"""Vaults, and vaults as a source of sandbox secrets."""

import json

import pytest

from hyperbrowser.client.managers.sync_manager.sandboxes.sandbox_processes import (
    SandboxProcessesApi,
)
from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.models import (
    CreateSandboxParams,
    CreateVaultParams,
    SandboxDetail,
    SandboxResolvedSecret,
    StoredEntry,
    UpdateVaultParams,
    Vault,
    VaultEntry,
)
from tests.test_credentials import mock_clients, respond
from tests.test_sandbox_wire_contract import SANDBOX_DETAIL_PAYLOAD
from tests.test_secrets import (
    AGENT_PROCESS,
    SECRET_ID,
    RuntimeScript,
    _sandbox_manager,
)

VAULT_ID = "3f1d2c4b-5a6e-4f70-8a9b-0c1d2e3f4a5b"
TOKEN_ID = "9e8d7c6b-5a4f-4e3d-8c2b-1a0f9e8d7c6b"
STORED_VAULT = {
    "id": VAULT_ID,
    "name": "github-login",
    "description": "",
    "entries": {
        "PASSWORD": {"name": "github-password", "secretId": SECRET_ID, "version": 3},
        "USERNAME": {"name": "github-username", "secretId": SECRET_ID, "version": None},
    },
    "createdAt": "2026-10-01T00:00:00Z",
    "updatedAt": "2026-10-01T00:00:00Z",
}


@pytest.fixture(params=[False, True], ids=["sync", "async"])
def sdk(request):
    yield from mock_clients(request.param)


def _body(request):
    return json.loads(request.content)


# --- models ---


def test_vaults_parse_stored_entries():
    vault = Vault.model_validate(STORED_VAULT)
    password = vault.entries["PASSWORD"]
    assert isinstance(password, VaultEntry)
    assert isinstance(password, StoredEntry)
    assert (password.name, password.secret_id, password.version) == (
        "github-password",
        SECRET_ID,
        3,
    )
    username = vault.entries["USERNAME"]
    assert isinstance(username, StoredEntry) and username.version is None
    assert Vault.model_validate(dict(STORED_VAULT, entries=None)).entries == {}


def test_a_stray_source_in_a_vault_response_is_ignored():
    for source in [
        {"type": "stored"},
        {"type": "1password", "tokenSecret": {"name": "op-token"}, "vault": "Eng"},
        None,
    ]:
        vault = Vault.model_validate(dict(STORED_VAULT, source=source))
        assert vault.name == "github-login"
        assert not hasattr(vault, "source")


# --- requests ---


def test_create_sends_entries_without_a_source(sdk):
    client, call, calls, outcomes = sdk
    respond(outcomes, STORED_VAULT, 201)
    respond(outcomes, STORED_VAULT, 201)

    vault = call(
        client.vaults.create,
        {
            "name": "github-login",
            "description": "GitHub",
            "entries": {
                "USERNAME": {"name": "github-username"},
                "PASSWORD": {"name": "github-password", "version": 3},
                "OTP": {"name": "github-otp", "version": "latest"},
            },
        },
    )
    assert calls[0].method == "POST" and calls[0].url.path == "/api/vaults"
    assert _body(calls[0]) == {
        "name": "github-login",
        "description": "GitHub",
        "entries": {
            "USERNAME": {"name": "github-username"},
            "PASSWORD": {"name": "github-password", "version": 3},
            "OTP": {"name": "github-otp", "version": "latest"},
        },
    }
    assert vault.id == VAULT_ID

    call(
        client.vaults.create,
        CreateVaultParams(
            name="github-otp",
            entries={"OTP": StoredEntry(name="github-otp", version=2)},
        ),
    )
    assert _body(calls[1]) == {
        "name": "github-otp",
        "entries": {"OTP": {"name": "github-otp", "version": 2}},
    }


def test_entries_read_from_a_vault_can_be_sent_back(sdk):
    client, call, calls, outcomes = sdk
    respond(outcomes, STORED_VAULT, 201)
    vault = Vault.model_validate(STORED_VAULT)

    call(
        client.vaults.create,
        CreateVaultParams(name="github-copy", entries=dict(vault.entries)),
    )
    # Only request members: no secretId.
    assert _body(calls[0])["entries"] == {
        "PASSWORD": {"name": "github-password", "version": 3},
        "USERNAME": {"name": "github-username"},
    }


def test_update_distinguishes_left_out_replaced_and_removed(sdk):
    client, call, calls, outcomes = sdk
    respond(outcomes, {"vaults": [STORED_VAULT], "totalCount": 1})
    respond(outcomes, STORED_VAULT)
    respond(outcomes, STORED_VAULT)
    respond(outcomes, STORED_VAULT)

    call(
        client.vaults.update,
        "github-login",
        {
            "description": None,
            "entries": {"OTP": None, "PASSWORD": {"name": "github-password"}},
        },
    )
    assert calls[0].url.path == "/api/vaults"
    assert dict(calls[0].url.params) == {"search": "github-login", "limit": "100"}
    assert calls[1].method == "PATCH"
    assert calls[1].url.path == f"/api/vaults/{VAULT_ID}"
    # None at the top level is "not given"; an entry set to None is removed.
    assert calls[1].content == (
        b'{"entries":{"OTP":null,"PASSWORD":{"name":"github-password"}}}'
    )

    call(
        client.vaults.update,
        VAULT_ID,
        UpdateVaultParams(
            description="GitHub",
            entries={"OTP": StoredEntry(name="github-otp", version="latest")},
        ),
    )
    assert calls[2].url.path == f"/api/vaults/{VAULT_ID}"
    assert calls[3].method == "PATCH"
    assert _body(calls[3]) == {
        "description": "GitHub",
        "entries": {"OTP": {"name": "github-otp", "version": "latest"}},
    }

    for bad in [
        {"source": {"vault": "Platform"}},
        {"entries": {"P": {"item": "i", "field": "f"}}},
    ]:
        with pytest.raises(ValueError):
            call(client.vaults.update, VAULT_ID, bad)
    assert len(calls) == 4


def test_list_get_and_delete_resolve_names_and_ids(sdk):
    client, call, calls, outcomes = sdk
    listing = {"vaults": [STORED_VAULT], "totalCount": 1, "page": 1, "perPage": 20}
    respond(outcomes, listing)
    respond(outcomes, listing)
    respond(outcomes, dict(STORED_VAULT, name="prod-db"))
    respond(outcomes, STORED_VAULT)
    respond(outcomes, {"deleted": True, "id": VAULT_ID, "name": "github-login"})
    respond(outcomes, {"code": "VAULT_NOT_FOUND", "message": "Vault not found"}, 404)
    respond(outcomes, {"vaults": [], "totalCount": 0})
    respond(outcomes, {"vaults": [dict(STORED_VAULT, name="github")], "totalCount": 1})

    result = call(client.vaults.list, {"page": 1, "limit": 20, "search": "git"})
    assert dict(calls[0].url.params) == {"page": "1", "limit": "20", "search": "git"}
    assert result.total_count == 1 and result.vaults[0].name == "github-login"

    assert call(client.vaults.get, " github-login ").id == VAULT_ID
    assert call(client.vaults.get, VAULT_ID).name == "prod-db"
    assert calls[2].url.path == f"/api/vaults/{VAULT_ID}"

    deleted = call(client.vaults.delete, VAULT_ID)
    assert calls[4].method == "DELETE" and deleted.name == "github-login"
    assert calls[4].url.path == f"/api/vaults/{VAULT_ID}"

    # A UUID-shaped key that isn't an ID falls back to a name search; names
    # match exactly.
    with pytest.raises(HyperbrowserError) as error:
        call(client.vaults.get, VAULT_ID)
    assert error.value.code == "VAULT_NOT_FOUND"
    with pytest.raises(HyperbrowserError) as error:
        call(client.vaults.get, "github-login")
    assert error.value.code == "VAULT_NOT_FOUND" and error.value.status_code == 404

    with pytest.raises(ValueError):
        call(client.vaults.list, {"limit": 101})


def test_vault_errors_keep_the_server_code(sdk):
    client, call, calls, outcomes = sdk
    respond(
        outcomes,
        {
            "code": "SECRET_TYPE_MISMATCH",
            "message": 'Secret "op-token" is an op_token; vault entries take stored secrets',
        },
        409,
    )
    with pytest.raises(HyperbrowserError) as error:
        call(
            client.vaults.create,
            {"name": "op", "entries": {"TOKEN": {"name": "op-token"}}},
        )
    assert error.value.code == "SECRET_TYPE_MISMATCH"
    assert error.value.status_code == 409
    # Writes are never retried.
    assert len(calls) == 1


# --- sandboxes ---

BINDINGS = [
    {
        "env": "USERNAME",
        "name": "github-username",
        "secretId": SECRET_ID,
        "version": 1,
        "source": {"type": "vault", "name": "github-login"},
    },
    {
        "env": "OTP",
        "name": "github-otp",
        "secretId": SECRET_ID,
        "version": 2,
        "secretType": "totp",
        "source": {"type": "secrets"},
        "overrides": [{"type": "vault", "name": "github-login"}],
    },
    {
        "env": "DB_PASS",
        "reference": "op://Engineering/Postgres/prod/password",
        "tokenSecret": "op-token",
        "source": {"type": "onePassword"},
    },
]


def test_bindings_describe_stored_totp_and_1password_variables():
    stored, totp, linked = [SandboxResolvedSecret.model_validate(b) for b in BINDINGS]
    assert stored.source is not None and stored.source.name == "github-login"
    assert stored.secret_type is None and stored.overrides == []
    assert totp.secret_type == "totp"
    assert totp.source is not None and totp.source.type == "secrets"
    assert [(o.type, o.name) for o in totp.overrides] == [("vault", "github-login")]
    assert (linked.name, linked.secret_id, linked.version) == (None, None, None)
    assert linked.reference == "op://Engineering/Postgres/prod/password"
    assert linked.token_secret == "op-token"
    assert linked.source is not None and linked.source.type == "onePassword"
    assert linked.source.name is None and linked.overrides == []


def test_sandbox_create_sends_a_vault_and_keeps_the_startup_bindings():
    params = CreateSandboxParams(
        image_name="node", vault="github-login", secrets={"OTP": "github-otp"}
    )
    assert params.model_dump(by_alias=True, exclude_none=True) == {
        "imageName": "node",
        "vault": "github-login",
        "secrets": {"OTP": {"name": "github-otp"}},
    }
    with pytest.raises(ValueError, match="only supported for image launches"):
        CreateSandboxParams(snapshot_name="snap", vault="github-login")

    manager, http = _sandbox_manager(
        {
            ("POST", "/sandbox"): (
                200,
                dict(SANDBOX_DETAIL_PAYLOAD, startupSecrets=BINDINGS),
            ),
            ("GET", "/sandbox/sbx_123"): (200, SANDBOX_DETAIL_PAYLOAD),
        }
    )
    sandbox = manager.create({"image_name": "node", "vault": "github-login"})
    assert http.calls[0]["json"] == {"imageName": "node", "vault": "github-login"}
    assert sandbox.startup_secrets is not None
    assert [b.env for b in sandbox.startup_secrets] == ["USERNAME", "OTP", "DB_PASS"]
    sandbox.refresh()
    assert sandbox.startup_secrets is not None


@pytest.mark.anyio
async def test_async_sandbox_create_with_a_vault_is_an_unknown_outcome_on_timeout():
    import httpx

    manager, http = _sandbox_manager(
        {("POST", "/sandbox"): httpx.ReadTimeout("timed out")}, async_client=True
    )
    with pytest.raises(HyperbrowserError) as error:
        await manager.create({"image_name": "node", "vault": "github-login"})
    assert error.value.code == "secret_process_outcome_unknown"
    assert error.value.retryable is False


def test_process_starts_with_a_vault_go_through_the_control_api():
    starts = []

    def start(payload):
        starts.append(payload)
        return {"process": AGENT_PROCESS, "secrets": BINDINGS}

    api = SandboxProcessesApi(RuntimeScript(), start, "sbx_123")

    handle = api.start("node app.js", vault="github-login")
    assert starts[-1] == {"command": "node app.js", "vault": "github-login"}
    assert handle.secrets is not None
    assert handle.secrets[2].reference == "op://Engineering/Postgres/prod/password"

    api.start(
        {"command": "node app.js", "vault": "github-login"},
        secrets={"OTP": "github-otp"},
    )
    assert starts[-1] == {
        "command": "node app.js",
        "secrets": {"OTP": {"name": "github-otp"}},
        "vault": "github-login",
    }

    with pytest.raises(HyperbrowserError, match="use_shell"):
        api.start({"command": "x", "use_shell": True}, vault="github-login")
    assert len(starts) == 2


@pytest.mark.anyio
async def test_async_sandbox_handles_route_vault_starts_to_the_control_api():
    manager, http = _sandbox_manager(
        {
            ("POST", "/sandbox/sbx_123/processes"): (
                200,
                {"process": AGENT_PROCESS, "secrets": BINDINGS},
            )
        },
        async_client=True,
    )
    sandbox = manager.attach(SandboxDetail(**SANDBOX_DETAIL_PAYLOAD))

    handle = await sandbox.processes.start("node app.js", vault="prod-db")

    assert http.calls[0]["json"] == {"command": "node app.js", "vault": "prod-db"}
    assert handle.secrets is not None and handle.secrets[1].secret_type == "totp"


@pytest.mark.parametrize(
    "params",
    [
        {"name": "bad name"},
        {"name": "v", "entries": {"1BAD": {"name": "s", "version": 0}}},
    ],
)
def test_vault_policy_errors_come_from_the_api(sdk, params):
    client, call, calls, outcomes = sdk
    respond(outcomes, {"error": "Invalid vault request"}, 400)
    with pytest.raises(HyperbrowserError) as error:
        call(client.vaults.create, params)
    assert error.value.status_code == 400
    assert len(calls) == 1
    assert _body(calls[0]) == params


@pytest.mark.parametrize(
    "params",
    [
        {"name": "v", "source": {}},
        {"name": "v", "entries": {"A": {"item": "i", "field": "f"}}},
    ],
)
def test_vault_unknown_members_and_missing_names_fail_locally(sdk, params):
    client, call, calls, outcomes = sdk
    with pytest.raises(ValueError):
        call(client.vaults.create, params)
    assert not calls
