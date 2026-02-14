import asyncio
from collections.abc import Mapping
from types import MappingProxyType, SimpleNamespace

import pytest

from hyperbrowser.client.managers.async_manager.computer_action import (
    ComputerActionManager as AsyncComputerActionManager,
)
from hyperbrowser.client.managers.async_manager.crawl import (
    CrawlManager as AsyncCrawlManager,
)
from hyperbrowser.client.managers.async_manager.extract import (
    ExtractManager as AsyncExtractManager,
)
from hyperbrowser.client.managers.async_manager.extension import (
    ExtensionManager as AsyncExtensionManager,
)
from hyperbrowser.client.managers.async_manager.profile import (
    ProfileManager as AsyncProfileManager,
)
from hyperbrowser.client.managers.async_manager.scrape import (
    BatchScrapeManager as AsyncBatchScrapeManager,
)
from hyperbrowser.client.managers.async_manager.scrape import (
    ScrapeManager as AsyncScrapeManager,
)
from hyperbrowser.client.managers.async_manager.team import (
    TeamManager as AsyncTeamManager,
)
from hyperbrowser.client.managers.async_manager.web.batch_fetch import (
    BatchFetchManager as AsyncBatchFetchManager,
)
from hyperbrowser.client.managers.async_manager.web.crawl import (
    WebCrawlManager as AsyncWebCrawlManager,
)
from hyperbrowser.client.managers.async_manager.web import (
    WebManager as AsyncWebManager,
)
from hyperbrowser.client.managers.async_manager.agents.browser_use import (
    BrowserUseManager as AsyncBrowserUseManager,
)
from hyperbrowser.client.managers.async_manager.agents.claude_computer_use import (
    ClaudeComputerUseManager as AsyncClaudeComputerUseManager,
)
from hyperbrowser.client.managers.async_manager.agents.cua import (
    CuaManager as AsyncCuaManager,
)
from hyperbrowser.client.managers.async_manager.agents.gemini_computer_use import (
    GeminiComputerUseManager as AsyncGeminiComputerUseManager,
)
from hyperbrowser.client.managers.async_manager.agents.hyper_agent import (
    HyperAgentManager as AsyncHyperAgentManager,
)
from hyperbrowser.client.managers.response_utils import parse_response_model
from hyperbrowser.client.managers.sync_manager.computer_action import (
    ComputerActionManager as SyncComputerActionManager,
)
from hyperbrowser.client.managers.sync_manager.crawl import (
    CrawlManager as SyncCrawlManager,
)
from hyperbrowser.client.managers.sync_manager.extract import (
    ExtractManager as SyncExtractManager,
)
from hyperbrowser.client.managers.sync_manager.extension import (
    ExtensionManager as SyncExtensionManager,
)
from hyperbrowser.client.managers.sync_manager.profile import (
    ProfileManager as SyncProfileManager,
)
from hyperbrowser.client.managers.sync_manager.scrape import (
    BatchScrapeManager as SyncBatchScrapeManager,
)
from hyperbrowser.client.managers.sync_manager.scrape import (
    ScrapeManager as SyncScrapeManager,
)
from hyperbrowser.client.managers.sync_manager.team import (
    TeamManager as SyncTeamManager,
)
from hyperbrowser.client.managers.sync_manager.web.batch_fetch import (
    BatchFetchManager as SyncBatchFetchManager,
)
from hyperbrowser.client.managers.sync_manager.web.crawl import (
    WebCrawlManager as SyncWebCrawlManager,
)
from hyperbrowser.client.managers.sync_manager.web import WebManager as SyncWebManager
from hyperbrowser.client.managers.sync_manager.agents.browser_use import (
    BrowserUseManager as SyncBrowserUseManager,
)
from hyperbrowser.client.managers.sync_manager.agents.claude_computer_use import (
    ClaudeComputerUseManager as SyncClaudeComputerUseManager,
)
from hyperbrowser.client.managers.sync_manager.agents.cua import (
    CuaManager as SyncCuaManager,
)
from hyperbrowser.client.managers.sync_manager.agents.gemini_computer_use import (
    GeminiComputerUseManager as SyncGeminiComputerUseManager,
)
from hyperbrowser.client.managers.sync_manager.agents.hyper_agent import (
    HyperAgentManager as SyncHyperAgentManager,
)
from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.models.extension import CreateExtensionParams
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


class _BrokenValueLookupMapping(Mapping[str, object]):
    def __init__(self, *, key: str, error: Exception):
        self._key = key
        self._error = error

    def __iter__(self):
        yield self._key

    def __len__(self) -> int:
        return 1

    def __getitem__(self, key: str) -> object:
        _ = key
        raise self._error


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


def test_parse_response_model_rejects_non_string_keys():
    with pytest.raises(
        HyperbrowserError,
        match="Expected basic operation response object keys to be strings",
    ):
        parse_response_model(
            {1: True},  # type: ignore[dict-item]
            model=BasicResponse,
            operation_name="basic operation",
        )


def test_parse_response_model_rejects_string_subclass_keys():
    class _Key(str):
        pass

    with pytest.raises(
        HyperbrowserError,
        match="Expected basic operation response object keys to be strings",
    ):
        parse_response_model(
            {_Key("success"): True},
            model=BasicResponse,
            operation_name="basic operation",
        )


def test_parse_response_model_sanitizes_operation_name_in_errors():
    with pytest.raises(
        HyperbrowserError,
        match="Expected basic\\?operation response to be an object",
    ):
        parse_response_model(
            ["bad"],  # type: ignore[arg-type]
            model=BasicResponse,
            operation_name="basic\toperation",
        )


def test_parse_response_model_wraps_operation_name_strip_failures():
    class _BrokenOperationName(str):
        def strip(self, chars=None):  # type: ignore[override]
            _ = chars
            raise RuntimeError("operation name strip exploded")

    with pytest.raises(HyperbrowserError, match="Failed to normalize operation_name") as exc_info:
        parse_response_model(
            {"success": True},
            model=BasicResponse,
            operation_name=_BrokenOperationName("basic operation"),
        )

    assert isinstance(exc_info.value.original_error, RuntimeError)


def test_parse_response_model_preserves_hyperbrowser_operation_name_strip_failures():
    class _BrokenOperationName(str):
        def strip(self, chars=None):  # type: ignore[override]
            _ = chars
            raise HyperbrowserError("custom operation name strip failure")

    with pytest.raises(
        HyperbrowserError, match="custom operation name strip failure"
    ) as exc_info:
        parse_response_model(
            {"success": True},
            model=BasicResponse,
            operation_name=_BrokenOperationName("basic operation"),
        )

    assert exc_info.value.original_error is None


def test_parse_response_model_wraps_non_string_operation_name_strip_results():
    class _BrokenOperationName(str):
        def strip(self, chars=None):  # type: ignore[override]
            _ = chars
            return object()

    with pytest.raises(HyperbrowserError, match="Failed to normalize operation_name") as exc_info:
        parse_response_model(
            {"success": True},
            model=BasicResponse,
            operation_name=_BrokenOperationName("basic operation"),
        )

    assert isinstance(exc_info.value.original_error, TypeError)


def test_parse_response_model_wraps_operation_name_string_subclass_strip_results():
    class _BrokenOperationName(str):
        class _NormalizedName(str):
            pass

        def strip(self, chars=None):  # type: ignore[override]
            _ = chars
            return self._NormalizedName("basic operation")

    with pytest.raises(HyperbrowserError, match="Failed to normalize operation_name") as exc_info:
        parse_response_model(
            {"success": True},
            model=BasicResponse,
            operation_name=_BrokenOperationName("basic operation"),
        )

    assert isinstance(exc_info.value.original_error, TypeError)


def test_parse_response_model_rejects_blank_operation_names():
    with pytest.raises(
        HyperbrowserError, match="operation_name must be a non-empty string"
    ):
        parse_response_model(
            {"success": True},
            model=BasicResponse,
            operation_name="   ",
        )


def test_parse_response_model_truncates_operation_name_in_errors():
    long_operation_name = "basic operation " + ("x" * 200)

    with pytest.raises(
        HyperbrowserError,
        match=(
            r"Expected basic operation x+\.\.\. \(truncated\) "
            r"response to be an object"
        ),
    ):
        parse_response_model(
            ["bad"],  # type: ignore[arg-type]
            model=BasicResponse,
            operation_name=long_operation_name,
        )


def test_parse_response_model_rejects_string_subclass_keys_before_value_reads():
    class _BrokenKey(str):
        def __iter__(self):
            raise RuntimeError("key iteration exploded")

    class _BrokenValueLookupMapping(Mapping[str, object]):
        def __iter__(self):
            yield _BrokenKey("success")

        def __len__(self) -> int:
            return 1

        def __getitem__(self, key: str) -> object:
            _ = key
            raise RuntimeError("cannot read value")

    with pytest.raises(
        HyperbrowserError,
        match="Expected basic operation response object keys to be strings",
    ) as exc_info:
        parse_response_model(
            _BrokenValueLookupMapping(),
            model=BasicResponse,
            operation_name="basic operation",
        )

    assert exc_info.value.original_error is None


def test_parse_response_model_wraps_mapping_read_failures():
    with pytest.raises(
        HyperbrowserError,
        match="Failed to read basic operation response keys",
    ) as exc_info:
        parse_response_model(
            _BrokenMapping({"success": True}),
            model=BasicResponse,
            operation_name="basic operation",
        )

    assert exc_info.value.original_error is not None


def test_parse_response_model_preserves_hyperbrowser_key_read_failures():
    class _BrokenMapping(Mapping[str, object]):
        def __iter__(self):
            raise HyperbrowserError("custom key read failure")

        def __len__(self) -> int:
            return 1

        def __getitem__(self, key: str) -> object:
            return key

    with pytest.raises(HyperbrowserError, match="custom key read failure") as exc_info:
        parse_response_model(
            _BrokenMapping(),
            model=BasicResponse,
            operation_name="basic operation",
        )

    assert exc_info.value.original_error is None


def test_parse_response_model_wraps_mapping_value_read_failures():
    with pytest.raises(
        HyperbrowserError,
        match="Failed to read basic operation response value for key 'success'",
    ) as exc_info:
        parse_response_model(
            _BrokenValueLookupMapping(
                key="success",
                error=RuntimeError("cannot read value"),
            ),
            model=BasicResponse,
            operation_name="basic operation",
        )

    assert exc_info.value.original_error is not None


def test_parse_response_model_sanitizes_key_display_in_value_read_failures():
    with pytest.raises(
        HyperbrowserError,
        match="Failed to read basic operation response value for key 'bad\\?key'",
    ) as exc_info:
        parse_response_model(
            _BrokenValueLookupMapping(
                key="bad\tkey",
                error=RuntimeError("cannot read value"),
            ),
            model=BasicResponse,
            operation_name="basic operation",
        )

    assert exc_info.value.original_error is not None


def test_parse_response_model_preserves_hyperbrowser_value_read_failures():
    with pytest.raises(HyperbrowserError, match="custom read failure") as exc_info:
        parse_response_model(
            _BrokenValueLookupMapping(
                key="success",
                error=HyperbrowserError("custom read failure"),
            ),
            model=BasicResponse,
            operation_name="basic operation",
        )

    assert exc_info.value.original_error is None


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
    session = SimpleNamespace(
        computer_action_endpoint="https://example.com/computer-action"
    )

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
    session = SimpleNamespace(
        computer_action_endpoint="https://example.com/computer-action"
    )

    async def run() -> None:
        with pytest.raises(
            HyperbrowserError,
            match="Expected computer action response to be an object",
        ):
            await manager.screenshot(session)

    asyncio.run(run())


@pytest.mark.parametrize(
    ("manager_class", "url_suffix", "expected_message"),
    [
        (
            SyncBrowserUseManager,
            "/task/browser-use/job_123/status",
            "Expected browser-use task status response to be an object",
        ),
        (
            SyncCuaManager,
            "/task/cua/job_123/status",
            "Expected cua task status response to be an object",
        ),
        (
            SyncClaudeComputerUseManager,
            "/task/claude-computer-use/job_123/status",
            "Expected claude computer use task status response to be an object",
        ),
        (
            SyncGeminiComputerUseManager,
            "/task/gemini-computer-use/job_123/status",
            "Expected gemini computer use task status response to be an object",
        ),
        (
            SyncHyperAgentManager,
            "/task/hyper-agent/job_123/status",
            "Expected hyper agent task status response to be an object",
        ),
        (
            SyncExtractManager,
            "/extract/job_123/status",
            "Expected extract status response to be an object",
        ),
        (
            SyncCrawlManager,
            "/crawl/job_123/status",
            "Expected crawl status response to be an object",
        ),
        (
            SyncBatchScrapeManager,
            "/scrape/batch/job_123/status",
            "Expected batch scrape status response to be an object",
        ),
        (
            SyncScrapeManager,
            "/scrape/job_123/status",
            "Expected scrape status response to be an object",
        ),
        (
            SyncBatchFetchManager,
            "/web/batch-fetch/job_123/status",
            "Expected batch fetch status response to be an object",
        ),
        (
            SyncWebCrawlManager,
            "/web/crawl/job_123/status",
            "Expected web crawl status response to be an object",
        ),
    ],
)
def test_sync_status_managers_reject_invalid_response_shape(
    manager_class, url_suffix: str, expected_message: str
):
    class _SyncTransport:
        def get(self, url, params=None, follow_redirects=False):
            _ = params
            _ = follow_redirects
            assert url.endswith(url_suffix)
            return _FakeResponse(["invalid"])

    manager = manager_class(_FakeClient(_SyncTransport()))

    with pytest.raises(HyperbrowserError, match=expected_message):
        manager.get_status("job_123")


@pytest.mark.parametrize(
    ("manager_class", "url_suffix", "expected_message"),
    [
        (
            AsyncBrowserUseManager,
            "/task/browser-use/job_123/status",
            "Expected browser-use task status response to be an object",
        ),
        (
            AsyncCuaManager,
            "/task/cua/job_123/status",
            "Expected cua task status response to be an object",
        ),
        (
            AsyncClaudeComputerUseManager,
            "/task/claude-computer-use/job_123/status",
            "Expected claude computer use task status response to be an object",
        ),
        (
            AsyncGeminiComputerUseManager,
            "/task/gemini-computer-use/job_123/status",
            "Expected gemini computer use task status response to be an object",
        ),
        (
            AsyncHyperAgentManager,
            "/task/hyper-agent/job_123/status",
            "Expected hyper agent task status response to be an object",
        ),
        (
            AsyncExtractManager,
            "/extract/job_123/status",
            "Expected extract status response to be an object",
        ),
        (
            AsyncCrawlManager,
            "/crawl/job_123/status",
            "Expected crawl status response to be an object",
        ),
        (
            AsyncBatchScrapeManager,
            "/scrape/batch/job_123/status",
            "Expected batch scrape status response to be an object",
        ),
        (
            AsyncScrapeManager,
            "/scrape/job_123/status",
            "Expected scrape status response to be an object",
        ),
        (
            AsyncBatchFetchManager,
            "/web/batch-fetch/job_123/status",
            "Expected batch fetch status response to be an object",
        ),
        (
            AsyncWebCrawlManager,
            "/web/crawl/job_123/status",
            "Expected web crawl status response to be an object",
        ),
    ],
)
def test_async_status_managers_reject_invalid_response_shape(
    manager_class, url_suffix: str, expected_message: str
):
    class _AsyncTransport:
        async def get(self, url, params=None, follow_redirects=False):
            _ = params
            _ = follow_redirects
            assert url.endswith(url_suffix)
            return _FakeResponse(["invalid"])

    manager = manager_class(_FakeClient(_AsyncTransport()))

    async def run() -> None:
        with pytest.raises(HyperbrowserError, match=expected_message):
            await manager.get_status("job_123")

    asyncio.run(run())


def test_sync_extension_manager_create_rejects_invalid_response_shape(tmp_path):
    class _SyncTransport:
        def post(self, url, data=None, files=None):
            _ = data
            _ = files
            assert url.endswith("/extensions/add")
            return _FakeResponse(["invalid"])

    manager = SyncExtensionManager(_FakeClient(_SyncTransport()))
    file_path = tmp_path / "extension.zip"
    file_path.write_bytes(b"extension-data")

    with pytest.raises(
        HyperbrowserError, match="Expected create extension response to be an object"
    ):
        manager.create(CreateExtensionParams(name="my-extension", file_path=file_path))


def test_async_extension_manager_create_rejects_invalid_response_shape(tmp_path):
    class _AsyncTransport:
        async def post(self, url, data=None, files=None):
            _ = data
            _ = files
            assert url.endswith("/extensions/add")
            return _FakeResponse(["invalid"])

    manager = AsyncExtensionManager(_FakeClient(_AsyncTransport()))
    file_path = tmp_path / "extension.zip"
    file_path.write_bytes(b"extension-data")

    async def run() -> None:
        with pytest.raises(
            HyperbrowserError,
            match="Expected create extension response to be an object",
        ):
            await manager.create(
                CreateExtensionParams(name="my-extension", file_path=file_path)
            )

    asyncio.run(run())
