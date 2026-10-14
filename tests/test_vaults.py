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
    OnePasswordEntry,
    OnePasswordVaultSource,
    SandboxDetail,
    SandboxResolvedSecret,
    StoredEntry,
    UpdateVaultParams,
    Vault,
    VaultOnePasswordEntry,
    VaultStoredEntry,
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
    "source": {"type": "stored"},
    "entries": {
        "PASSWORD": {"name": "github-password", "secretId": SECRET_ID, "version": 3},
        "USERNAME": {"name": "github-username", "secretId": SECRET_ID, "version": None},
    },
    "createdAt": "2026-10-01T00:00:00Z",
    "updatedAt": "2026-10-01T00:00:00Z",
}
ONEPASSWORD_VAULT = {
    "id": VAULT_ID,
    "name": "prod-db",
    "description": "",
    "source": {
        "type": "1password",
        "tokenSecret": {"name": "op-token", "secretId": TOKEN_ID},
        "vault": "Engineering",
    },
    "entries": {
        "DB_PASS": {
            "item": "Postgres",
            "section": "prod",
            "field": "password",
            "reference": "op://Engineering/Postgres/prod/password",
        }
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


def test_vaults_parse_both_sources_and_entry_kinds():
    stored = Vault.model_validate(STORED_VAULT)
    assert stored.source.type == "stored"
    password = stored.entries["PASSWORD"]
    assert isinstance(password, VaultStoredEntry)
    assert isinstance(password, StoredEntry)
    assert (password.name, password.secret_id, password.version) == (
        "github-password",
        SECRET_ID,
        3,
    )
    username = stored.entries["USERNAME"]
    assert isinstance(username, StoredEntry) and username.version is None

    linked = Vault.model_validate(ONEPASSWORD_VAULT)
    assert linked.source.type == "1password"
    assert linked.source.vault == "Engineering"
    assert linked.source.token_secret is not None
    assert linked.source.token_secret.name == "op-token"
    assert linked.source.token_secret.secret_id == TOKEN_ID
    entry = linked.entries["DB_PASS"]
    assert isinstance(entry, VaultOnePasswordEntry)
    assert (entry.item, entry.section, entry.field) == ("Postgres", "prod", "password")
    assert entry.reference == "op://Engineering/Postgres/prod/password"


def test_vaults_from_apis_without_sources_or_with_new_ones_parse():
    legacy = dict(STORED_VAULT)
    del legacy["source"]
    assert Vault.model_validate(legacy).source.type == "stored"
    assert Vault.model_validate(dict(legacy, source=None, entries=None)).entries == {}

    future = Vault.model_validate(
        dict(STORED_VAULT, source={"type": "keychain", "account": "x"}, entries={})
    )
    assert future.source.type == "keychain"
    assert future.source.model_dump()["account"] == "x"


# --- requests ---


def test_create_sends_stored_and_1password_vaults(sdk):
    client, call, calls, outcomes = sdk
    respond(outcomes, STORED_VAULT, 201)
    respond(outcomes, ONEPASSWORD_VAULT, 201)

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
            name="prod-db",
            source=OnePasswordVaultSource(
                type="1password", token_secret="op-token", vault="Engineering"
            ),
            entries={
                "DB_PASS": OnePasswordEntry(
                    item="Postgres", section="prod", field="password"
                ),
                "DB_OTP": OnePasswordEntry(
                    item="Postgres", field="one-time password?attribute=otp"
                ),
            },
        ),
    )
    assert _body(calls[1]) == {
        "name": "prod-db",
        "source": {
            "type": "1password",
            "tokenSecret": "op-token",
            "vault": "Engineering",
        },
        "entries": {
            "DB_PASS": {"item": "Postgres", "section": "prod", "field": "password"},
            "DB_OTP": {"item": "Postgres", "field": "one-time password?attribute=otp"},
        },
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


def _onepassword(entries):
    return {
        "name": "op",
        "source": {"type": "1password", "token_secret": "op-token", "vault": "Eng"},
        "entries": entries,
    }


@pytest.mark.parametrize(
    "params,message",
    [
        ({"name": "bad name"}, "Invalid secret name"),
        ({"name": "v", "entries": {"1PASS": {"name": "s"}}}, "entry name"),
        ({"name": "v", "entries": {"__proto__": {"name": "s"}}}, "entry name"),
        ({"name": "v", "entries": {"P" * 257: {"name": "s"}}}, "entry name"),
        ({"name": "v", "entries": {"P": {"name": "bad name"}}}, "secret name"),
        ({"name": "v", "entries": {"P": {"name": "s", "version": 0}}}, "version"),
        ({"name": "v", "entries": {"P": {"name": "s", "version": "next"}}}, "version"),
        (
            {"name": "v", "entries": {f"E{i}": {"name": "s"} for i in range(33)}},
            "at most 32",
        ),
        ({"name": "v", "entries": {"P": {"item": "i", "field": "f"}}}, "stored vault"),
        (_onepassword({"P": {"name": "s"}}), "1Password vault"),
        (_onepassword({"P": {"item": "a/b", "field": "f"}}), "item"),
        (_onepassword({"P": {"item": "a?b", "field": "f"}}), "item"),
        (_onepassword({"P": {"item": "..", "field": "f"}}), "item"),
        (_onepassword({"P": {"item": "a​b", "field": "f"}}), "item"),
        (_onepassword({"P": {"item": "a\nb", "field": "f"}}), "item"),
        (_onepassword({"P": {"item": "i" * 257, "field": "f"}}), "longer"),
        (_onepassword({"P": {"item": "i", "section": "", "field": "f"}}), "section"),
        (_onepassword({"P": {"item": "i", "field": "."}}), "field"),
        (_onepassword({"P": {"item": "i", "field": "f?"}}), "query"),
        (_onepassword({"P": {"item": "i", "field": "f?Attr=otp"}}), "query"),
        (_onepassword({"P": {"item": "i", "field": "f?a=b&c"}}), "query"),
        (_onepassword({"P": {"item": "i", "field": "f?a=b?c"}}), "query"),
        (_onepassword({"P": {"item": "i" * 250, "field": "f" * 256}}), "512 bytes"),
        (
            {"name": "op", "source": {"type": "1password", "vault": "Eng"}},
            "token_secret",
        ),
        (
            {
                "name": "op",
                "source": {"type": "1password", "token_secret": "t", "vault": "a/b"},
            },
            "1Password vault",
        ),
        ({"name": "op", "source": {"type": "keychain"}}, "type"),
    ],
)
def test_invalid_vaults_fail_before_http(sdk, params, message):
    client, call, calls, outcomes = sdk
    with pytest.raises(ValueError, match=message):
        call(client.vaults.create, params)
    assert not calls


def test_1password_names_allow_what_the_server_allows():
    CreateVaultParams.model_validate(
        _onepassword(
            {
                "A": {"item": "My Login (old)", "field": "password"},
                "B": {"item": "x" * 256, "section": "Ünïcødé ✓", "field": "f"},
                "C": {"item": "i", "field": "otp?attribute=otp&ssh-format=openssh"},
                "D": {"item": "...", "field": ".hidden"},
            }
        )
    )


def test_update_distinguishes_left_out_replaced_and_removed(sdk):
    client, call, calls, outcomes = sdk
    respond(outcomes, {"vaults": [STORED_VAULT], "totalCount": 1})
    respond(outcomes, STORED_VAULT)
    respond(outcomes, ONEPASSWORD_VAULT)
    respond(outcomes, ONEPASSWORD_VAULT)

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
            description="Prod",
            source={"vault": "Platform"},  # type: ignore[arg-type]
        ),
    )
    assert calls[2].url.path == f"/api/vaults/{VAULT_ID}"
    assert calls[3].method == "PATCH"
    assert _body(calls[3]) == {"description": "Prod", "source": {"vault": "Platform"}}

    for bad in [{}, {"description": None}, {"source": {}}, {"entries": {"1X": None}}]:
        with pytest.raises(ValueError):
            call(client.vaults.update, VAULT_ID, bad)
    assert len(calls) == 4


def test_list_get_and_delete_resolve_names_and_ids(sdk):
    client, call, calls, outcomes = sdk
    listing = {"vaults": [STORED_VAULT], "totalCount": 1, "page": 1, "perPage": 20}
    respond(outcomes, listing)
    respond(outcomes, listing)
    respond(outcomes, ONEPASSWORD_VAULT)
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
            "message": "a 1Password vault's token must be an op_token secret",
        },
        409,
    )
    with pytest.raises(HyperbrowserError) as error:
        call(
            client.vaults.create,
            {
                "name": "op",
                "source": {"type": "1password", "token_secret": "pw", "vault": "Eng"},
            },
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
        "source": {"type": "vault", "name": "prod-db"},
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
    with pytest.raises(ValueError):
        CreateSandboxParams(image_name="node", vault="bad name")

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

    with pytest.raises(ValueError):
        api.start("node app.js", vault="bad name")
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
