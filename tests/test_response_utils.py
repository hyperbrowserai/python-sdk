import asyncio
from collections.abc import Mapping
from types import MappingProxyType, SimpleNamespace

import pytest

from hyperbrowser.client.managers.async_manager.computer_action import (
    ComputerActionManager as AsyncComputerActionManager,
)
from hyperbrowser.client.managers.async_manager.profile import (
    ProfileManager as AsyncProfileManager,
)
from hyperbrowser.client.managers.async_manager.team import (
    TeamManager as AsyncTeamManager,
)
from hyperbrowser.client.managers.async_manager.web import (
    WebManager as AsyncWebManager,
)
from hyperbrowser.client.managers.response_utils import parse_response_model
from hyperbrowser.client.managers.sync_manager.computer_action import (
    ComputerActionManager as SyncComputerActionManager,
)
from hyperbrowser.client.managers.sync_manager.profile import (
    ProfileManager as SyncProfileManager,
)
from hyperbrowser.client.managers.sync_manager.team import (
    TeamManager as SyncTeamManager,
)
from hyperbrowser.client.managers.sync_manager.web import WebManager as SyncWebManager
from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.models.session import BasicResponse
from hyperbrowser.models.web.search import WebSearchParams


class _FakeResponse:
    def __init__(self, data):
        self.data = data


class _FakeClient:
    def __init__(self, transport):
        self.transport = transport
        self.sessions = None

    def _build_url(self, path: str) -> str:
        return f"https://api.hyperbrowser.ai/api{path}"


class _BrokenMapping(Mapping[str, object]):
    def __init__(self, payload):
        self._payload = payload

    def __iter__(self):
        raise RuntimeError("broken mapping iteration")

    def __len__(self) -> int:
        return len(self._payload)

    def __getitem__(self, key: str) -> object:
        return self._payload[key]


def test_parse_response_model_parses_mapping_payloads():
    response_model = parse_response_model(
        {"success": True},
        model=BasicResponse,
        operation_name="basic operation",
    )

    assert isinstance(response_model, BasicResponse)
    assert response_model.success is True


def test_parse_response_model_supports_mapping_proxy_payloads():
    response_model = parse_response_model(
        MappingProxyType({"success": True}),
        model=BasicResponse,
        operation_name="basic operation",
    )

    assert response_model.success is True


def test_parse_response_model_rejects_non_mapping_payloads():
    with pytest.raises(
        HyperbrowserError,
        match="Expected basic operation response to be an object",
    ):
        parse_response_model(
            ["bad"],  # type: ignore[arg-type]
            model=BasicResponse,
            operation_name="basic operation",
        )


def test_parse_response_model_wraps_mapping_read_failures():
    with pytest.raises(
        HyperbrowserError,
        match="Failed to read basic operation response data",
    ) as exc_info:
        parse_response_model(
            _BrokenMapping({"success": True}),
            model=BasicResponse,
            operation_name="basic operation",
        )

    assert exc_info.value.original_error is not None


def test_sync_team_manager_rejects_invalid_response_shape():
    class _SyncTransport:
        def get(self, url, params=None, follow_redirects=False):
            _ = params
            _ = follow_redirects
            assert url.endswith("/team/credit-info")
            return _FakeResponse(["invalid"])

    manager = SyncTeamManager(_FakeClient(_SyncTransport()))

    with pytest.raises(
        HyperbrowserError, match="Expected team credit info response to be an object"
    ):
        manager.get_credit_info()


def test_async_team_manager_rejects_invalid_response_shape():
    class _AsyncTransport:
        async def get(self, url, params=None, follow_redirects=False):
            _ = params
            _ = follow_redirects
            assert url.endswith("/team/credit-info")
            return _FakeResponse(["invalid"])

    manager = AsyncTeamManager(_FakeClient(_AsyncTransport()))

    async def run() -> None:
        with pytest.raises(
            HyperbrowserError,
            match="Expected team credit info response to be an object",
        ):
            await manager.get_credit_info()

    asyncio.run(run())


def test_sync_profile_manager_rejects_invalid_response_shape():
    class _SyncTransport:
        def post(self, url, data=None, files=None):
            _ = data
            _ = files
            assert url.endswith("/profile")
            return _FakeResponse(["invalid"])

    manager = SyncProfileManager(_FakeClient(_SyncTransport()))

    with pytest.raises(
        HyperbrowserError, match="Expected create profile response to be an object"
    ):
        manager.create()


def test_async_profile_manager_rejects_invalid_response_shape():
    class _AsyncTransport:
        async def post(self, url, data=None, files=None):
            _ = data
            _ = files
            assert url.endswith("/profile")
            return _FakeResponse(["invalid"])

    manager = AsyncProfileManager(_FakeClient(_AsyncTransport()))

    async def run() -> None:
        with pytest.raises(
            HyperbrowserError, match="Expected create profile response to be an object"
        ):
            await manager.create()

    asyncio.run(run())


def test_sync_web_manager_search_rejects_invalid_response_shape():
    class _SyncTransport:
        def post(self, url, data=None, files=None):
            _ = data
            _ = files
            assert url.endswith("/web/search")
            return _FakeResponse(["invalid"])

    manager = SyncWebManager(_FakeClient(_SyncTransport()))

    with pytest.raises(
        HyperbrowserError, match="Expected web search response to be an object"
    ):
        manager.search(WebSearchParams(query="q"))


def test_async_web_manager_search_rejects_invalid_response_shape():
    class _AsyncTransport:
        async def post(self, url, data=None, files=None):
            _ = data
            _ = files
            assert url.endswith("/web/search")
            return _FakeResponse(["invalid"])

    manager = AsyncWebManager(_FakeClient(_AsyncTransport()))

    async def run() -> None:
        with pytest.raises(
            HyperbrowserError, match="Expected web search response to be an object"
        ):
            await manager.search(WebSearchParams(query="q"))

    asyncio.run(run())


def test_sync_computer_action_manager_rejects_invalid_response_shape():
    class _SyncTransport:
        def post(self, url, data=None, files=None):
            _ = data
            _ = files
            assert url == "https://example.com/computer-action"
            return _FakeResponse(["invalid"])

    manager = SyncComputerActionManager(_FakeClient(_SyncTransport()))
    session = SimpleNamespace(computer_action_endpoint="https://example.com/computer-action")

    with pytest.raises(
        HyperbrowserError, match="Expected computer action response to be an object"
    ):
        manager.screenshot(session)


def test_async_computer_action_manager_rejects_invalid_response_shape():
    class _AsyncTransport:
        async def post(self, url, data=None, files=None):
            _ = data
            _ = files
            assert url == "https://example.com/computer-action"
            return _FakeResponse(["invalid"])

    manager = AsyncComputerActionManager(_FakeClient(_AsyncTransport()))
    session = SimpleNamespace(computer_action_endpoint="https://example.com/computer-action")

    async def run() -> None:
        with pytest.raises(
            HyperbrowserError,
            match="Expected computer action response to be an object",
        ):
            await manager.screenshot(session)

    asyncio.run(run())
