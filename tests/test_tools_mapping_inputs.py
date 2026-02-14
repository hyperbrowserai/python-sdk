import asyncio
from collections.abc import Iterator, Mapping
from types import MappingProxyType

import pytest

from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.models.scrape import StartScrapeJobParams
from hyperbrowser.tools import WebsiteExtractTool, WebsiteScrapeTool


class _Response:
    def __init__(self, data):
        self.data = data


class _ScrapeManager:
    def __init__(self):
        self.last_params = None

    def start_and_wait(self, params: StartScrapeJobParams):
        self.last_params = params
        return _Response(type("Data", (), {"markdown": "ok"})())


class _Client:
    def __init__(self):
        self.scrape = _ScrapeManager()


class _AsyncScrapeManager:
    async def start_and_wait(self, params: StartScrapeJobParams):
        return _Response(type("Data", (), {"markdown": "ok"})())


class _AsyncClient:
    def __init__(self):
        self.scrape = _AsyncScrapeManager()


class _AsyncExtractManager:
    async def start_and_wait(self, params):
        return _Response({"ok": True})


class _AsyncExtractClient:
    def __init__(self):
        self.extract = _AsyncExtractManager()


def _run_scrape_tool_sync(params: Mapping[str, object]) -> None:
    client = _Client()
    WebsiteScrapeTool.runnable(client, params)


def _run_scrape_tool_async(params: Mapping[str, object]) -> None:
    async def run() -> None:
        client = _AsyncClient()
        await WebsiteScrapeTool.async_runnable(client, params)

    asyncio.run(run())


def test_tool_wrappers_accept_mapping_inputs():
    client = _Client()
    params = MappingProxyType({"url": "https://example.com"})

    output = WebsiteScrapeTool.runnable(client, params)

    assert output == "ok"
    assert isinstance(client.scrape.last_params, StartScrapeJobParams)


def test_tool_wrappers_reject_non_mapping_inputs():
    client = _Client()

    with pytest.raises(HyperbrowserError, match="tool params must be a mapping"):
        WebsiteScrapeTool.runnable(client, ["https://example.com"])  # type: ignore[arg-type]


def test_extract_tool_wrapper_rejects_non_mapping_inputs():
    class _ExtractManager:
        def start_and_wait(self, params):
            return type("_Response", (), {"data": {"ok": True}})()

    class _ExtractClient:
        def __init__(self):
            self.extract = _ExtractManager()

    client = _ExtractClient()
    with pytest.raises(HyperbrowserError, match="tool params must be a mapping"):
        WebsiteExtractTool.runnable(client, "bad")  # type: ignore[arg-type]


def test_async_tool_wrappers_reject_non_mapping_inputs():
    async def run() -> None:
        client = _AsyncClient()
        with pytest.raises(HyperbrowserError, match="tool params must be a mapping"):
            await WebsiteScrapeTool.async_runnable(
                client,
                ["https://example.com"],  # type: ignore[arg-type]
            )

        extract_client = _AsyncExtractClient()
        with pytest.raises(HyperbrowserError, match="tool params must be a mapping"):
            await WebsiteExtractTool.async_runnable(
                extract_client,
                "bad",  # type: ignore[arg-type]
            )

    asyncio.run(run())


def test_tool_wrappers_reject_non_string_param_keys():
    client = _Client()

    with pytest.raises(HyperbrowserError, match="tool params keys must be strings"):
        WebsiteScrapeTool.runnable(
            client,
            {1: "https://example.com"},  # type: ignore[dict-item]
        )


def test_tool_wrappers_reject_blank_param_keys():
    client = _Client()

    with pytest.raises(HyperbrowserError, match="tool params keys must not be empty"):
        WebsiteScrapeTool.runnable(
            client,
            {"   ": "https://example.com"},
        )


def test_tool_wrappers_reject_param_keys_with_surrounding_whitespace():
    client = _Client()

    with pytest.raises(
        HyperbrowserError,
        match="tool params keys must not contain leading or trailing whitespace",
    ):
        WebsiteScrapeTool.runnable(
            client,
            {" url ": "https://example.com"},
        )


def test_tool_wrappers_reject_param_keys_with_control_characters():
    client = _Client()

    with pytest.raises(
        HyperbrowserError, match="tool params keys must not contain control characters"
    ):
        WebsiteScrapeTool.runnable(
            client,
            {"u\trl": "https://example.com"},
        )


def test_tool_wrappers_wrap_param_key_read_failures():
    class _BrokenKeyMapping(Mapping[str, object]):
        def __iter__(self) -> Iterator[str]:
            raise RuntimeError("cannot iterate keys")

        def __len__(self) -> int:
            return 1

        def __getitem__(self, key: str) -> object:
            _ = key
            return "ignored"

    client = _Client()

    with pytest.raises(
        HyperbrowserError, match="Failed to read tool params keys"
    ) as exc_info:
        WebsiteScrapeTool.runnable(client, _BrokenKeyMapping())

    assert exc_info.value.original_error is not None


def test_tool_wrappers_wrap_param_value_read_failures():
    class _BrokenValueMapping(Mapping[str, object]):
        def __iter__(self) -> Iterator[str]:
            yield "url"

        def __len__(self) -> int:
            return 1

        def __getitem__(self, key: str) -> object:
            _ = key
            raise RuntimeError("cannot read value")

    client = _Client()

    with pytest.raises(
        HyperbrowserError, match="Failed to read tool param 'url'"
    ) as exc_info:
        WebsiteScrapeTool.runnable(client, _BrokenValueMapping())

    assert exc_info.value.original_error is not None


def test_tool_wrappers_preserve_hyperbrowser_param_value_read_failures():
    class _BrokenValueMapping(Mapping[str, object]):
        def __iter__(self) -> Iterator[str]:
            yield "url"

        def __len__(self) -> int:
            return 1

        def __getitem__(self, key: str) -> object:
            _ = key
            raise HyperbrowserError("custom param value read failure")

    client = _Client()

    with pytest.raises(
        HyperbrowserError, match="custom param value read failure"
    ) as exc_info:
        WebsiteScrapeTool.runnable(client, _BrokenValueMapping())

    assert exc_info.value.original_error is None


@pytest.mark.parametrize("runner", [_run_scrape_tool_sync, _run_scrape_tool_async])
def test_tool_wrappers_fall_back_for_unreadable_param_value_read_keys(runner):
    class _BrokenKey(str):
        def __new__(cls, value: str):
            instance = super().__new__(cls, value)
            instance._iteration_count = 0
            return instance

        def __iter__(self):
            self._iteration_count += 1
            if self._iteration_count > 1:
                raise RuntimeError("cannot iterate param key")
            return super().__iter__()

    class _BrokenValueMapping(Mapping[str, object]):
        def __iter__(self) -> Iterator[str]:
            yield _BrokenKey("url")

        def __len__(self) -> int:
            return 1

        def __getitem__(self, key: str) -> object:
            _ = key
            raise RuntimeError("cannot read value")

    with pytest.raises(
        HyperbrowserError, match="Failed to read tool param '<unreadable key>'"
    ) as exc_info:
        runner(_BrokenValueMapping())

    assert isinstance(exc_info.value.original_error, RuntimeError)


@pytest.mark.parametrize("runner", [_run_scrape_tool_sync, _run_scrape_tool_async])
def test_tool_wrappers_wrap_param_key_strip_failures(runner):
    class _BrokenStripKey(str):
        def strip(self, chars=None):  # type: ignore[override]
            _ = chars
            raise RuntimeError("tool param key strip exploded")

    with pytest.raises(
        HyperbrowserError, match="Failed to normalize tool param key"
    ) as exc_info:
        runner({_BrokenStripKey("url"): "https://example.com"})

    assert isinstance(exc_info.value.original_error, RuntimeError)


@pytest.mark.parametrize("runner", [_run_scrape_tool_sync, _run_scrape_tool_async])
def test_tool_wrappers_preserve_hyperbrowser_param_key_strip_failures(runner):
    class _BrokenStripKey(str):
        def strip(self, chars=None):  # type: ignore[override]
            _ = chars
            raise HyperbrowserError("custom tool param key strip failure")

    with pytest.raises(
        HyperbrowserError, match="custom tool param key strip failure"
    ) as exc_info:
        runner({_BrokenStripKey("url"): "https://example.com"})

    assert exc_info.value.original_error is None


@pytest.mark.parametrize("runner", [_run_scrape_tool_sync, _run_scrape_tool_async])
def test_tool_wrappers_wrap_non_string_param_key_strip_results(runner):
    class _BrokenStripKey(str):
        def strip(self, chars=None):  # type: ignore[override]
            _ = chars
            return object()

    with pytest.raises(
        HyperbrowserError, match="Failed to normalize tool param key"
    ) as exc_info:
        runner({_BrokenStripKey("url"): "https://example.com"})

    assert isinstance(exc_info.value.original_error, TypeError)


@pytest.mark.parametrize("runner", [_run_scrape_tool_sync, _run_scrape_tool_async])
def test_tool_wrappers_wrap_param_key_empty_check_length_failures(runner):
    class _BrokenStripKey(str):
        class _NormalizedKey(str):
            def __len__(self):
                raise RuntimeError("tool param key length exploded")

        def strip(self, chars=None):  # type: ignore[override]
            _ = chars
            return self._NormalizedKey("url")

    with pytest.raises(
        HyperbrowserError, match="Failed to normalize tool param key"
    ) as exc_info:
        runner({_BrokenStripKey("url"): "https://example.com"})

    assert isinstance(exc_info.value.original_error, RuntimeError)


@pytest.mark.parametrize("runner", [_run_scrape_tool_sync, _run_scrape_tool_async])
def test_tool_wrappers_preserve_hyperbrowser_param_key_empty_check_length_failures(
    runner,
):
    class _BrokenStripKey(str):
        class _NormalizedKey(str):
            def __len__(self):
                raise HyperbrowserError("custom tool param key length failure")

        def strip(self, chars=None):  # type: ignore[override]
            _ = chars
            return self._NormalizedKey("url")

    with pytest.raises(
        HyperbrowserError, match="custom tool param key length failure"
    ) as exc_info:
        runner({_BrokenStripKey("url"): "https://example.com"})

    assert exc_info.value.original_error is None


@pytest.mark.parametrize("runner", [_run_scrape_tool_sync, _run_scrape_tool_async])
def test_tool_wrappers_wrap_param_key_character_validation_failures(runner):
    class _BrokenIterKey(str):
        def strip(self, chars=None):  # type: ignore[override]
            _ = chars
            return self

        def __iter__(self):
            raise RuntimeError("tool param key iteration exploded")

    with pytest.raises(
        HyperbrowserError, match="Failed to validate tool param key characters"
    ) as exc_info:
        runner({_BrokenIterKey("url"): "https://example.com"})

    assert isinstance(exc_info.value.original_error, RuntimeError)


@pytest.mark.parametrize("runner", [_run_scrape_tool_sync, _run_scrape_tool_async])
def test_tool_wrappers_preserve_hyperbrowser_param_key_character_validation_failures(
    runner,
):
    class _BrokenIterKey(str):
        def strip(self, chars=None):  # type: ignore[override]
            _ = chars
            return self

        def __iter__(self):
            raise HyperbrowserError("custom tool param key iteration failure")

    with pytest.raises(
        HyperbrowserError, match="custom tool param key iteration failure"
    ) as exc_info:
        runner({_BrokenIterKey("url"): "https://example.com"})

    assert exc_info.value.original_error is None
