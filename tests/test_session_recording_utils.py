import asyncio
from types import MappingProxyType

import pytest

from hyperbrowser.client.managers.async_manager.session import (
    SessionManager as AsyncSessionManager,
)
from hyperbrowser.client.managers.session_utils import (
    parse_session_recordings_response_data,
)
from hyperbrowser.client.managers.sync_manager.session import (
    SessionManager as SyncSessionManager,
)
from hyperbrowser.exceptions import HyperbrowserError


class _FakeResponse:
    def __init__(self, data):
        self.data = data


class _SyncTransport:
    def __init__(self, response_data):
        self._response_data = response_data

    def get(self, url, params=None, follow_redirects=False):
        _ = params
        _ = follow_redirects
        assert url.endswith("/session/session_123/recording")
        return _FakeResponse(self._response_data)


class _AsyncTransport:
    def __init__(self, response_data):
        self._response_data = response_data

    async def get(self, url, params=None, follow_redirects=False):
        _ = params
        _ = follow_redirects
        assert url.endswith("/session/session_123/recording")
        return _FakeResponse(self._response_data)


class _FakeClient:
    def __init__(self, transport):
        self.transport = transport

    def _build_url(self, path: str) -> str:
        return f"https://api.hyperbrowser.ai/api{path}"


def test_parse_session_recordings_response_data_parses_list_payloads():
    recordings = parse_session_recordings_response_data(
        [
            {
                "type": 1,
                "data": {"event": "click"},
                "timestamp": 123,
            }
        ]
    )

    assert len(recordings) == 1
    assert recordings[0].type == 1
    assert recordings[0].timestamp == 123


def test_parse_session_recordings_response_data_accepts_mapping_proxy_items():
    recordings = parse_session_recordings_response_data(
        [
            MappingProxyType(
                {
                    "type": 1,
                    "data": {"event": "scroll"},
                    "timestamp": 321,
                }
            )
        ]
    )

    assert len(recordings) == 1
    assert recordings[0].timestamp == 321


def test_parse_session_recordings_response_data_rejects_non_list_payloads():
    with pytest.raises(
        HyperbrowserError,
        match="Expected session recording response to be a list of objects",
    ):
        parse_session_recordings_response_data({"type": 1})  # type: ignore[arg-type]


def test_parse_session_recordings_response_data_rejects_non_mapping_items():
    with pytest.raises(
        HyperbrowserError,
        match="Expected session recording object at index 0 but got str",
    ):
        parse_session_recordings_response_data(["invalid-item"])


def test_parse_session_recordings_response_data_wraps_invalid_items():
    with pytest.raises(
        HyperbrowserError, match="Failed to parse session recording at index 0"
    ) as exc_info:
        parse_session_recordings_response_data(
            [
                {
                    "type": 1,
                    # missing required fields
                }
            ]
        )

    assert exc_info.value.original_error is not None


def test_parse_session_recordings_response_data_wraps_unreadable_list_iteration():
    class _BrokenRecordingList(list):
        def __iter__(self):
            raise RuntimeError("cannot iterate recordings")

    with pytest.raises(
        HyperbrowserError, match="Failed to iterate session recording response list"
    ) as exc_info:
        parse_session_recordings_response_data(_BrokenRecordingList([{}]))

    assert exc_info.value.original_error is not None


def test_parse_session_recordings_response_data_preserves_hyperbrowser_iteration_errors():
    class _BrokenRecordingList(list):
        def __iter__(self):
            raise HyperbrowserError("custom recording iteration failure")

    with pytest.raises(
        HyperbrowserError, match="custom recording iteration failure"
    ) as exc_info:
        parse_session_recordings_response_data(_BrokenRecordingList([{}]))

    assert exc_info.value.original_error is None


def test_sync_session_manager_get_recording_uses_recording_parser():
    manager = SyncSessionManager(
        _FakeClient(
            _SyncTransport(
                [
                    {
                        "type": 1,
                        "data": {"event": "click"},
                        "timestamp": 123,
                    }
                ]
            )
        )
    )

    recordings = manager.get_recording("session_123")

    assert len(recordings) == 1
    assert recordings[0].timestamp == 123


def test_async_session_manager_get_recording_uses_recording_parser():
    manager = AsyncSessionManager(
        _FakeClient(
            _AsyncTransport(
                [
                    {
                        "type": 1,
                        "data": {"event": "click"},
                        "timestamp": 123,
                    }
                ]
            )
        )
    )

    async def run():
        return await manager.get_recording("session_123")

    recordings = asyncio.run(run())

    assert len(recordings) == 1
    assert recordings[0].timestamp == 123


def test_sync_session_manager_get_recording_rejects_invalid_payload_shapes():
    manager = SyncSessionManager(_FakeClient(_SyncTransport({"bad": "payload"})))

    with pytest.raises(
        HyperbrowserError,
        match="Expected session recording response to be a list of objects",
    ):
        manager.get_recording("session_123")


def test_async_session_manager_get_recording_rejects_invalid_payload_shapes():
    manager = AsyncSessionManager(_FakeClient(_AsyncTransport({"bad": "payload"})))

    async def run():
        with pytest.raises(
            HyperbrowserError,
            match="Expected session recording response to be a list of objects",
        ):
            await manager.get_recording("session_123")

    asyncio.run(run())
