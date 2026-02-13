import asyncio
from types import MappingProxyType

import pytest

from hyperbrowser import AsyncHyperbrowser, Hyperbrowser
from hyperbrowser.config import ClientConfig
from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.transport.async_transport import AsyncTransport
from hyperbrowser.transport.sync import SyncTransport


def test_sync_transport_accepts_custom_headers():
    transport = SyncTransport(
        api_key="test-key",
        headers={"X-Correlation-Id": "abc123", "User-Agent": "custom-agent"},
    )
    try:
        assert transport.client.headers["x-api-key"] == "test-key"
        assert transport.client.headers["X-Correlation-Id"] == "abc123"
        assert transport.client.headers["User-Agent"] == "custom-agent"
    finally:
        transport.close()


def test_sync_transport_rejects_non_string_header_pairs():
    with pytest.raises(HyperbrowserError, match="headers must be a mapping"):
        SyncTransport(api_key="test-key", headers={"X-Correlation-Id": 123})  # type: ignore[dict-item]


def test_sync_transport_rejects_invalid_api_key_values():
    with pytest.raises(HyperbrowserError, match="api_key must be a string"):
        SyncTransport(api_key=None)  # type: ignore[arg-type]
    with pytest.raises(HyperbrowserError, match="api_key must not be empty"):
        SyncTransport(api_key="   ")
    with pytest.raises(
        HyperbrowserError, match="api_key must not contain control characters"
    ):
        SyncTransport(api_key="bad\nkey")


def test_sync_transport_rejects_empty_header_name():
    with pytest.raises(HyperbrowserError, match="header names must not be empty"):
        SyncTransport(api_key="test-key", headers={"   ": "value"})


def test_sync_transport_rejects_invalid_header_name_characters():
    with pytest.raises(
        HyperbrowserError,
        match="header names must contain only valid HTTP token characters",
    ):
        SyncTransport(api_key="test-key", headers={"X Trace": "value"})


def test_sync_transport_rejects_overly_long_header_names():
    long_header_name = "X-" + ("a" * 255)

    with pytest.raises(
        HyperbrowserError, match="header names must be 256 characters or fewer"
    ):
        SyncTransport(api_key="test-key", headers={long_header_name: "value"})


def test_sync_transport_rejects_header_newline_values():
    with pytest.raises(
        HyperbrowserError, match="headers must not contain newline characters"
    ):
        SyncTransport(api_key="test-key", headers={"X-Correlation-Id": "bad\nvalue"})


def test_sync_transport_rejects_header_control_character_values():
    with pytest.raises(
        HyperbrowserError, match="headers must not contain control characters"
    ):
        SyncTransport(api_key="test-key", headers={"X-Correlation-Id": "bad\tvalue"})


def test_async_transport_accepts_custom_headers():
    async def run() -> None:
        transport = AsyncTransport(
            api_key="test-key",
            headers={"X-Correlation-Id": "abc123", "User-Agent": "custom-agent"},
        )
        try:
            assert transport.client.headers["x-api-key"] == "test-key"
            assert transport.client.headers["X-Correlation-Id"] == "abc123"
            assert transport.client.headers["User-Agent"] == "custom-agent"
        finally:
            await transport.close()

    asyncio.run(run())


def test_async_transport_rejects_non_string_header_pairs():
    with pytest.raises(HyperbrowserError, match="headers must be a mapping"):
        AsyncTransport(api_key="test-key", headers={"X-Correlation-Id": 123})  # type: ignore[dict-item]


def test_async_transport_rejects_invalid_api_key_values():
    with pytest.raises(HyperbrowserError, match="api_key must be a string"):
        AsyncTransport(api_key=None)  # type: ignore[arg-type]
    with pytest.raises(HyperbrowserError, match="api_key must not be empty"):
        AsyncTransport(api_key="   ")
    with pytest.raises(
        HyperbrowserError, match="api_key must not contain control characters"
    ):
        AsyncTransport(api_key="bad\nkey")


def test_async_transport_rejects_empty_header_name():
    with pytest.raises(HyperbrowserError, match="header names must not be empty"):
        AsyncTransport(api_key="test-key", headers={"   ": "value"})


def test_async_transport_rejects_invalid_header_name_characters():
    with pytest.raises(
        HyperbrowserError,
        match="header names must contain only valid HTTP token characters",
    ):
        AsyncTransport(api_key="test-key", headers={"X Trace": "value"})


def test_async_transport_rejects_overly_long_header_names():
    long_header_name = "X-" + ("a" * 255)

    with pytest.raises(
        HyperbrowserError, match="header names must be 256 characters or fewer"
    ):
        AsyncTransport(api_key="test-key", headers={long_header_name: "value"})


def test_async_transport_rejects_header_newline_values():
    with pytest.raises(
        HyperbrowserError, match="headers must not contain newline characters"
    ):
        AsyncTransport(api_key="test-key", headers={"X-Correlation-Id": "bad\nvalue"})


def test_async_transport_rejects_header_control_character_values():
    with pytest.raises(
        HyperbrowserError, match="headers must not contain control characters"
    ):
        AsyncTransport(api_key="test-key", headers={"X-Correlation-Id": "bad\tvalue"})


def test_sync_client_config_headers_are_applied_to_transport():
    client = Hyperbrowser(
        config=ClientConfig(api_key="test-key", headers={"X-Team-Trace": "team-1"})
    )
    try:
        assert client.transport.client.headers["X-Team-Trace"] == "team-1"
    finally:
        client.close()


def test_sync_client_constructor_headers_are_applied_to_transport():
    headers = {"X-Team-Trace": "team-2"}
    client = Hyperbrowser(api_key="test-key", headers=headers)
    headers["X-Team-Trace"] = "mutated"
    try:
        assert client.transport.client.headers["X-Team-Trace"] == "team-2"
    finally:
        client.close()


def test_async_client_config_headers_are_applied_to_transport():
    async def run() -> None:
        client = AsyncHyperbrowser(
            config=ClientConfig(api_key="test-key", headers={"X-Team-Trace": "team-1"})
        )
        try:
            assert client.transport.client.headers["X-Team-Trace"] == "team-1"
        finally:
            await client.close()

    asyncio.run(run())


def test_async_client_constructor_headers_are_applied_to_transport():
    async def run() -> None:
        headers = {"X-Team-Trace": "team-2"}
        client = AsyncHyperbrowser(api_key="test-key", headers=headers)
        headers["X-Team-Trace"] = "mutated"
        try:
            assert client.transport.client.headers["X-Team-Trace"] == "team-2"
        finally:
            await client.close()

    asyncio.run(run())


def test_sync_client_constructor_accepts_mapping_headers():
    source_headers = {"X-Team-Trace": "team-mapping-sync"}
    mapping_headers = MappingProxyType(source_headers)
    client = Hyperbrowser(api_key="test-key", headers=mapping_headers)
    source_headers["X-Team-Trace"] = "mutated"
    try:
        assert client.transport.client.headers["X-Team-Trace"] == "team-mapping-sync"
    finally:
        client.close()


def test_async_client_constructor_accepts_mapping_headers():
    async def run() -> None:
        source_headers = {"X-Team-Trace": "team-mapping-async"}
        mapping_headers = MappingProxyType(source_headers)
        client = AsyncHyperbrowser(api_key="test-key", headers=mapping_headers)
        source_headers["X-Team-Trace"] = "mutated"
        try:
            assert (
                client.transport.client.headers["X-Team-Trace"] == "team-mapping-async"
            )
        finally:
            await client.close()

    asyncio.run(run())


def test_sync_client_constructor_reads_headers_from_environment(monkeypatch):
    monkeypatch.setenv("HYPERBROWSER_HEADERS", '{"X-Team-Trace":"env-sync"}')
    client = Hyperbrowser(api_key="test-key")
    try:
        assert client.transport.client.headers["X-Team-Trace"] == "env-sync"
    finally:
        client.close()


def test_async_client_constructor_reads_headers_from_environment(monkeypatch):
    monkeypatch.setenv("HYPERBROWSER_HEADERS", '{"X-Team-Trace":"env-async"}')

    async def run() -> None:
        client = AsyncHyperbrowser(api_key="test-key")
        try:
            assert client.transport.client.headers["X-Team-Trace"] == "env-async"
        finally:
            await client.close()

    asyncio.run(run())


def test_client_constructor_rejects_invalid_env_headers(monkeypatch):
    monkeypatch.setenv("HYPERBROWSER_HEADERS", "{invalid")

    with pytest.raises(HyperbrowserError, match="HYPERBROWSER_HEADERS"):
        Hyperbrowser(api_key="test-key")


def test_client_constructor_with_explicit_headers_ignores_invalid_env_headers(
    monkeypatch,
):
    monkeypatch.setenv("HYPERBROWSER_HEADERS", "{invalid")
    client = Hyperbrowser(
        api_key="test-key",
        headers={"X-Team-Trace": "constructor-value"},
    )
    try:
        assert client.transport.client.headers["X-Team-Trace"] == "constructor-value"
    finally:
        client.close()


def test_client_constructor_with_config_ignores_invalid_env_headers(monkeypatch):
    monkeypatch.setenv("HYPERBROWSER_HEADERS", "{invalid")
    client = Hyperbrowser(config=ClientConfig(api_key="test-key"))
    try:
        assert client.transport.client.headers["x-api-key"] == "test-key"
    finally:
        client.close()


def test_async_client_constructor_with_explicit_headers_ignores_invalid_env_headers(
    monkeypatch,
):
    monkeypatch.setenv("HYPERBROWSER_HEADERS", "{invalid")

    async def run() -> None:
        client = AsyncHyperbrowser(
            api_key="test-key",
            headers={"X-Team-Trace": "constructor-value"},
        )
        try:
            assert (
                client.transport.client.headers["X-Team-Trace"] == "constructor-value"
            )
        finally:
            await client.close()

    asyncio.run(run())


def test_async_client_constructor_with_config_ignores_invalid_env_headers(monkeypatch):
    monkeypatch.setenv("HYPERBROWSER_HEADERS", "{invalid")

    async def run() -> None:
        client = AsyncHyperbrowser(config=ClientConfig(api_key="test-key"))
        try:
            assert client.transport.client.headers["x-api-key"] == "test-key"
        finally:
            await client.close()

    asyncio.run(run())


def test_client_constructor_headers_override_environment_headers(monkeypatch):
    monkeypatch.setenv("HYPERBROWSER_HEADERS", '{"X-Team-Trace":"env-value"}')
    client = Hyperbrowser(
        api_key="test-key",
        headers={"X-Team-Trace": "constructor-value"},
    )
    try:
        assert client.transport.client.headers["X-Team-Trace"] == "constructor-value"
    finally:
        client.close()


def test_client_constructor_rejects_mixed_config_and_direct_args():
    with pytest.raises(TypeError, match="Pass either `config`"):
        Hyperbrowser(
            config=ClientConfig(api_key="test-key"),
            headers={"X-Team-Trace": "team-1"},
        )


def test_async_client_constructor_rejects_mixed_config_and_direct_args():
    with pytest.raises(TypeError, match="Pass either `config`"):
        AsyncHyperbrowser(
            config=ClientConfig(api_key="test-key"),
            headers={"X-Team-Trace": "team-1"},
        )
