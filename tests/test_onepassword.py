"""1Password fields as a per-request source of sandbox secrets."""

import pytest

from hyperbrowser.client.managers.async_manager.sandboxes.sandbox_processes import (
    SandboxProcessesApi as AsyncSandboxProcessesApi,
)
from hyperbrowser.client.managers.sync_manager.sandboxes.sandbox_processes import (
    SandboxProcessesApi,
)
from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.models import (
    CreateSandboxParams,
    OnePasswordField,
    OnePasswordSource,
    SandboxDetail,
    SandboxResolvedSecret,
)
from tests.test_sandbox_wire_contract import SANDBOX_DETAIL_PAYLOAD
from tests.test_secrets import (
    AGENT_PROCESS,
    RESULT,
    AsyncRuntimeScript,
    RuntimeScript,
    _sandbox_manager,
)

SOURCE = {
    "token": "op-token",
    "vault": "Dev Vault for Testing",
    "fields": {
        "SC_USER": {"item": "scrapingcourse login", "field": "username"},
        "SC_OTP": {
            "item": "scrapingcourse login",
            "section": "Security",
            "field": "otp?attribute=totp",
        },
    },
}
WIRE = {
    "token": "op-token",
    "vault": "Dev Vault for Testing",
    "fields": {
        "SC_USER": {"item": "scrapingcourse login", "field": "username"},
        "SC_OTP": {
            "item": "scrapingcourse login",
            "section": "Security",
            "field": "otp?attribute=totp",
        },
    },
}
BINDINGS = [
    {
        "env": "SC_USER",
        "reference": "op://Dev Vault for Testing/scrapingcourse login/username",
        "tokenSecret": "op-token",
        "source": {"type": "onePassword"},
    }
]


def _with_field(**field):
    return dict(SOURCE, fields={"X": dict({"item": "i", "field": "f"}, **field)})


def test_bindings_describe_1password_variables():
    binding = SandboxResolvedSecret.model_validate(BINDINGS[0])
    assert binding.reference == (
        "op://Dev Vault for Testing/scrapingcourse login/username"
    )
    assert binding.token_secret == "op-token"
    assert binding.source is not None and binding.source.type == "onePassword"
    assert (binding.name, binding.secret_id, binding.version) == (None, None, None)
    assert binding.secret_type is None and binding.overrides == []


# --- sandbox create ---


def test_create_params_send_one_password_as_onePassword():
    model = OnePasswordSource(
        token="op-token",
        vault="Dev Vault for Testing",
        fields={
            "SC_USER": OnePasswordField(item="scrapingcourse login", field="username"),
            "SC_OTP": OnePasswordField(
                item="scrapingcourse login",
                section="Security",
                field="otp?attribute=totp",
            ),
        },
    )
    for source in [SOURCE, model]:
        params = CreateSandboxParams(
            image_name="node", one_password=source, secrets={"API_KEY": "k"}
        )
        assert params.model_dump(by_alias=True, exclude_none=True) == {
            "imageName": "node",
            "secrets": {"API_KEY": {"name": "k"}},
            "onePassword": WIRE,
        }
    with pytest.raises(ValueError, match="only supported for image launches"):
        CreateSandboxParams(snapshot_name="snap", one_password=SOURCE)


@pytest.mark.parametrize("async_client", [False, True], ids=["sync", "async"])
@pytest.mark.anyio
async def test_create_sends_one_password_and_keeps_the_startup_bindings(async_client):
    manager, http = _sandbox_manager(
        {
            ("POST", "/sandbox"): (
                200,
                dict(SANDBOX_DETAIL_PAYLOAD, startupSecrets=BINDINGS),
            )
        },
        async_client=async_client,
    )
    result = manager.create({"image_name": "node", "one_password": SOURCE})
    sandbox = await result if async_client else result

    assert http.calls[0]["json"] == {"imageName": "node", "onePassword": WIRE}
    assert sandbox.startup_secrets is not None
    assert sandbox.startup_secrets[0].source.type == "onePassword"


@pytest.mark.anyio
async def test_async_create_with_one_password_is_an_unknown_outcome_on_timeout():
    import httpx

    manager, _ = _sandbox_manager(
        {("POST", "/sandbox"): httpx.ReadTimeout("timed out")}, async_client=True
    )
    with pytest.raises(HyperbrowserError) as error:
        await manager.create({"image_name": "node", "one_password": SOURCE})
    assert error.value.code == "secret_process_outcome_unknown"
    assert error.value.retryable is False


# --- process start and exec ---


def test_starts_and_execs_with_one_password_go_through_the_control_api():
    starts = []

    def start(payload):
        starts.append(payload)
        return {"process": AGENT_PROCESS, "secrets": BINDINGS}

    api = SandboxProcessesApi(RuntimeScript(waits=[RESULT]), start, "sbx_123")

    handle = api.start("node app.js", one_password=SOURCE)
    assert starts[-1] == {"command": "node app.js", "onePassword": WIRE}
    assert handle.secrets is not None
    assert handle.secrets[0].token_secret == "op-token"

    result = api.exec(
        {"command": "node app.js", "one_password": SOURCE, "env": {"MODE": "x"}},
        vault="github-login",
        secrets={"API_KEY": "provider-key"},
    )
    assert result.stdout == "ok\n"
    assert starts[-1] == {
        "command": "node app.js",
        "env": {"MODE": "x"},
        "secrets": {"API_KEY": {"name": "provider-key"}},
        "vault": "github-login",
        "onePassword": WIRE,
    }

    with pytest.raises(HyperbrowserError, match="use_shell"):
        api.start({"command": "x", "use_shell": True}, one_password=SOURCE)
    assert len(starts) == 2


@pytest.mark.anyio
async def test_async_starts_and_execs_with_one_password_go_through_the_control_api():
    starts = []

    async def start(payload):
        starts.append(payload)
        return {"process": AGENT_PROCESS, "secrets": BINDINGS}

    api = AsyncSandboxProcessesApi(AsyncRuntimeScript(waits=[RESULT]), start, "sbx_123")

    handle = await api.start("node app.js", one_password=SOURCE)
    assert handle.secrets is not None and handle.secrets[0].env == "SC_USER"
    result = await api.exec(
        "node app.js", one_password=OnePasswordSource.model_validate(SOURCE)
    )
    assert result.stdout == "ok\n"
    assert starts == [
        {"command": "node app.js", "onePassword": WIRE},
        {"command": "node app.js", "onePassword": WIRE},
    ]


@pytest.mark.parametrize("async_client", [False, True], ids=["sync", "async"])
@pytest.mark.anyio
async def test_sandbox_handles_send_one_password_to_the_processes_route(async_client):
    manager, http = _sandbox_manager(
        {
            ("POST", "/sandbox/sbx_123/processes"): (
                200,
                {"process": AGENT_PROCESS, "secrets": BINDINGS},
            )
        },
        async_client=async_client,
    )
    sandbox = manager.attach(SandboxDetail(**SANDBOX_DETAIL_PAYLOAD))

    result = sandbox.processes.start("node app.js", one_password=SOURCE)
    handle = await result if async_client else result

    assert http.calls[0]["path"] == "/sandbox/sbx_123/processes"
    assert http.calls[0]["json"] == {"command": "node app.js", "onePassword": WIRE}
    assert handle.secrets is not None and handle.secrets[0].reference is not None


# --- local checks ---


def test_names_allow_what_the_server_allows():
    OnePasswordSource.model_validate(
        dict(
            SOURCE,
            fields={
                "A": {"item": "My Login (old)", "field": "password"},
                "B": {"item": "x" * 256, "section": "Ünïcødé ✓", "field": "f"},
                "C": {"item": "i", "field": "otp?attribute=otp&ssh-format=openssh"},
                "D": {"item": "...", "field": ".hidden"},
                # An astral character is 2 UTF-16 units: 256 in all.
                "E": {"item": "\U0001f600" * 64 + "e" * 128, "field": "f"},
            },
        )
    )
    # op://V/<250>/<250>/fff is exactly 512 bytes.
    OnePasswordSource.model_validate(
        dict(
            SOURCE,
            vault="V",
            fields={"X": {"item": "i" * 250, "section": "s" * 250, "field": "fff"}},
        )
    )


@pytest.mark.parametrize("async_client", [False, True], ids=["sync", "async"])
@pytest.mark.anyio
async def test_source_conflicts_are_rejected_by_the_control_api(async_client):
    manager, http = _sandbox_manager(
        {
            ("POST", "/sandbox"): (
                400,
                {
                    "code": "SECRET_SOURCES_INVALID",
                    "message": "SC_USER is set by secrets and by onePassword",
                },
            )
        },
        async_client=async_client,
    )
    with pytest.raises(HyperbrowserError) as error:
        result = manager.create(
            {
                "image_name": "node",
                "one_password": SOURCE,
                "secrets": {"SC_USER": "user"},
            }
        )
        if async_client:
            await result
    assert error.value.code == "SECRET_SOURCES_INVALID"
    assert error.value.retryable is False
    assert len(http.calls) == 1
    assert http.calls[0]["json"]["onePassword"] == WIRE
    assert http.calls[0]["json"]["secrets"] == {"SC_USER": {"name": "user"}}


@pytest.mark.parametrize(
    "source", [dict(SOURCE, tokenSecret="op-token"), _with_field(label="extra")]
)
def test_unknown_source_members_fail_locally(source):
    with pytest.raises(ValueError):
        OnePasswordSource.model_validate(source)
