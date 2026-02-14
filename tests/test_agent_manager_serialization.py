import asyncio
from types import MappingProxyType, SimpleNamespace
from typing import Any, Tuple, Type

import pytest

from hyperbrowser.client.managers.async_manager.agents.claude_computer_use import (
    ClaudeComputerUseManager as AsyncClaudeComputerUseManager,
)
from hyperbrowser.client.managers.async_manager.agents.gemini_computer_use import (
    GeminiComputerUseManager as AsyncGeminiComputerUseManager,
)
from hyperbrowser.client.managers.async_manager.agents.hyper_agent import (
    HyperAgentManager as AsyncHyperAgentManager,
)
from hyperbrowser.client.managers.sync_manager.agents.claude_computer_use import (
    ClaudeComputerUseManager as SyncClaudeComputerUseManager,
)
from hyperbrowser.client.managers.sync_manager.agents.gemini_computer_use import (
    GeminiComputerUseManager as SyncGeminiComputerUseManager,
)
from hyperbrowser.client.managers.sync_manager.agents.hyper_agent import (
    HyperAgentManager as SyncHyperAgentManager,
)
from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.models.agents.claude_computer_use import (
    StartClaudeComputerUseTaskParams,
)
from hyperbrowser.models.agents.gemini_computer_use import (
    StartGeminiComputerUseTaskParams,
)
from hyperbrowser.models.agents.hyper_agent import StartHyperAgentTaskParams


class _SyncTransport:
    def __init__(self) -> None:
        self.calls = []

    def post(self, url: str, data=None) -> SimpleNamespace:
        self.calls.append((url, data))
        return SimpleNamespace(data={"jobId": "job_sync_1"})


class _AsyncTransport:
    def __init__(self) -> None:
        self.calls = []

    async def post(self, url: str, data=None) -> SimpleNamespace:
        self.calls.append((url, data))
        return SimpleNamespace(data={"jobId": "job_async_1"})


class _SyncClient:
    def __init__(self) -> None:
        self.transport = _SyncTransport()

    def _build_url(self, path: str) -> str:
        return path


class _AsyncClient:
    def __init__(self) -> None:
        self.transport = _AsyncTransport()

    def _build_url(self, path: str) -> str:
        return path


_SyncCase = Tuple[
    str,
    Type[Any],
    Type[Any],
    str,
    str,
]
_AsyncCase = _SyncCase

SYNC_CASES: tuple[_SyncCase, ...] = (
    (
        "claude",
        SyncClaudeComputerUseManager,
        StartClaudeComputerUseTaskParams,
        "/task/claude-computer-use",
        "Failed to serialize Claude Computer Use start params",
    ),
    (
        "gemini",
        SyncGeminiComputerUseManager,
        StartGeminiComputerUseTaskParams,
        "/task/gemini-computer-use",
        "Failed to serialize Gemini Computer Use start params",
    ),
    (
        "hyper-agent",
        SyncHyperAgentManager,
        StartHyperAgentTaskParams,
        "/task/hyper-agent",
        "Failed to serialize HyperAgent start params",
    ),
)

ASYNC_CASES: tuple[_AsyncCase, ...] = (
    (
        "claude",
        AsyncClaudeComputerUseManager,
        StartClaudeComputerUseTaskParams,
        "/task/claude-computer-use",
        "Failed to serialize Claude Computer Use start params",
    ),
    (
        "gemini",
        AsyncGeminiComputerUseManager,
        StartGeminiComputerUseTaskParams,
        "/task/gemini-computer-use",
        "Failed to serialize Gemini Computer Use start params",
    ),
    (
        "hyper-agent",
        AsyncHyperAgentManager,
        StartHyperAgentTaskParams,
        "/task/hyper-agent",
        "Failed to serialize HyperAgent start params",
    ),
)


def _build_params(params_class: Type[Any]) -> Any:
    return params_class(task="open docs")


@pytest.mark.parametrize(
    "_, manager_class, params_class, expected_url, __",
    SYNC_CASES,
    ids=[case[0] for case in SYNC_CASES],
)
def test_sync_agent_start_serializes_params(
    _: str,
    manager_class: Type[Any],
    params_class: Type[Any],
    expected_url: str,
    __: str,
):
    client = _SyncClient()
    manager = manager_class(client)

    response = manager.start(_build_params(params_class))

    assert response.job_id == "job_sync_1"
    url, payload = client.transport.calls[0]
    assert url == expected_url
    assert payload == {"task": "open docs"}


@pytest.mark.parametrize(
    "_, manager_class, params_class, __, expected_error",
    SYNC_CASES,
    ids=[case[0] for case in SYNC_CASES],
)
def test_sync_agent_start_wraps_param_serialization_errors(
    _: str,
    manager_class: Type[Any],
    params_class: Type[Any],
    __: str,
    expected_error: str,
    monkeypatch: pytest.MonkeyPatch,
):
    manager = manager_class(_SyncClient())
    params = _build_params(params_class)

    def _raise_model_dump_error(*args, **kwargs):
        _ = args
        _ = kwargs
        raise RuntimeError("broken model_dump")

    monkeypatch.setattr(params_class, "model_dump", _raise_model_dump_error)

    with pytest.raises(HyperbrowserError, match=expected_error) as exc_info:
        manager.start(params)

    assert isinstance(exc_info.value.original_error, RuntimeError)


@pytest.mark.parametrize(
    "_, manager_class, params_class, __, expected_error",
    SYNC_CASES,
    ids=[case[0] for case in SYNC_CASES],
)
def test_sync_agent_start_preserves_hyperbrowser_serialization_errors(
    _: str,
    manager_class: Type[Any],
    params_class: Type[Any],
    __: str,
    expected_error: str,
    monkeypatch: pytest.MonkeyPatch,
):
    manager = manager_class(_SyncClient())
    params = _build_params(params_class)

    def _raise_model_dump_error(*args, **kwargs):
        _ = args
        _ = kwargs
        raise HyperbrowserError("custom model_dump failure")

    monkeypatch.setattr(params_class, "model_dump", _raise_model_dump_error)

    with pytest.raises(
        HyperbrowserError, match="custom model_dump failure"
    ) as exc_info:
        manager.start(params)

    assert exc_info.value.original_error is None


@pytest.mark.parametrize(
    "_, manager_class, params_class, __, expected_error",
    SYNC_CASES,
    ids=[case[0] for case in SYNC_CASES],
)
def test_sync_agent_start_rejects_non_dict_serialized_params(
    _: str,
    manager_class: Type[Any],
    params_class: Type[Any],
    __: str,
    expected_error: str,
    monkeypatch: pytest.MonkeyPatch,
):
    manager = manager_class(_SyncClient())
    params = _build_params(params_class)

    monkeypatch.setattr(
        params_class,
        "model_dump",
        lambda *args, **kwargs: MappingProxyType({"task": "open docs"}),
    )

    with pytest.raises(HyperbrowserError, match=expected_error) as exc_info:
        manager.start(params)

    assert exc_info.value.original_error is None


@pytest.mark.parametrize(
    "_, manager_class, params_class, expected_url, __",
    ASYNC_CASES,
    ids=[case[0] for case in ASYNC_CASES],
)
def test_async_agent_start_serializes_params(
    _: str,
    manager_class: Type[Any],
    params_class: Type[Any],
    expected_url: str,
    __: str,
):
    client = _AsyncClient()
    manager = manager_class(client)

    async def run() -> None:
        response = await manager.start(_build_params(params_class))
        assert response.job_id == "job_async_1"
        url, payload = client.transport.calls[0]
        assert url == expected_url
        assert payload == {"task": "open docs"}

    asyncio.run(run())


@pytest.mark.parametrize(
    "_, manager_class, params_class, __, expected_error",
    ASYNC_CASES,
    ids=[case[0] for case in ASYNC_CASES],
)
def test_async_agent_start_wraps_param_serialization_errors(
    _: str,
    manager_class: Type[Any],
    params_class: Type[Any],
    __: str,
    expected_error: str,
    monkeypatch: pytest.MonkeyPatch,
):
    manager = manager_class(_AsyncClient())
    params = _build_params(params_class)

    def _raise_model_dump_error(*args, **kwargs):
        _ = args
        _ = kwargs
        raise RuntimeError("broken model_dump")

    monkeypatch.setattr(params_class, "model_dump", _raise_model_dump_error)

    async def run() -> None:
        with pytest.raises(HyperbrowserError, match=expected_error) as exc_info:
            await manager.start(params)
        assert isinstance(exc_info.value.original_error, RuntimeError)

    asyncio.run(run())


@pytest.mark.parametrize(
    "_, manager_class, params_class, __, expected_error",
    ASYNC_CASES,
    ids=[case[0] for case in ASYNC_CASES],
)
def test_async_agent_start_preserves_hyperbrowser_serialization_errors(
    _: str,
    manager_class: Type[Any],
    params_class: Type[Any],
    __: str,
    expected_error: str,
    monkeypatch: pytest.MonkeyPatch,
):
    manager = manager_class(_AsyncClient())
    params = _build_params(params_class)

    def _raise_model_dump_error(*args, **kwargs):
        _ = args
        _ = kwargs
        raise HyperbrowserError("custom model_dump failure")

    monkeypatch.setattr(params_class, "model_dump", _raise_model_dump_error)

    async def run() -> None:
        with pytest.raises(
            HyperbrowserError, match="custom model_dump failure"
        ) as exc_info:
            await manager.start(params)
        assert exc_info.value.original_error is None

    asyncio.run(run())


@pytest.mark.parametrize(
    "_, manager_class, params_class, __, expected_error",
    ASYNC_CASES,
    ids=[case[0] for case in ASYNC_CASES],
)
def test_async_agent_start_rejects_non_dict_serialized_params(
    _: str,
    manager_class: Type[Any],
    params_class: Type[Any],
    __: str,
    expected_error: str,
    monkeypatch: pytest.MonkeyPatch,
):
    manager = manager_class(_AsyncClient())
    params = _build_params(params_class)

    monkeypatch.setattr(
        params_class,
        "model_dump",
        lambda *args, **kwargs: MappingProxyType({"task": "open docs"}),
    )

    async def run() -> None:
        with pytest.raises(HyperbrowserError, match=expected_error) as exc_info:
            await manager.start(params)
        assert exc_info.value.original_error is None

    asyncio.run(run())
