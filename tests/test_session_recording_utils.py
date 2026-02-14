import asyncio
from collections.abc import Iterator, Mapping
from types import MappingProxyType

import pytest

from hyperbrowser.client.managers.async_manager.session import (
    SessionManager as AsyncSessionManager,
)
from hyperbrowser.client.managers.session_utils import (
    parse_session_recordings_response_data,
    parse_session_response_model,
)
from hyperbrowser.client.managers.sync_manager.session import (
    SessionManager as SyncSessionManager,
)
from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.models.session import BasicResponse


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

    def put(self, url, data=None):
        _ = data
        assert url.endswith("/session/session_123/stop")
        return _FakeResponse(self._response_data)


class _AsyncTransport:
    def __init__(self, response_data):
        self._response_data = response_data

    async def get(self, url, params=None, follow_redirects=False):
        _ = params
        _ = follow_redirects
        assert url.endswith("/session/session_123/recording")
        return _FakeResponse(self._response_data)

    async def put(self, url, data=None):
        _ = data
        assert url.endswith("/session/session_123/stop")
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


def test_parse_session_response_model_parses_mapping_payloads():
    result = parse_session_response_model(
        {"success": True},
        model=BasicResponse,
        operation_name="session stop",
    )

    assert isinstance(result, BasicResponse)
    assert result.success is True


def test_parse_session_response_model_accepts_mapping_proxy_payloads():
    result = parse_session_response_model(
        MappingProxyType({"success": True}),
        model=BasicResponse,
        operation_name="session stop",
    )

    assert result.success is True


def test_parse_session_response_model_rejects_non_mapping_payloads():
    with pytest.raises(
        HyperbrowserError, match="Expected session stop response to be an object"
    ):
        parse_session_response_model(
            ["invalid"],  # type: ignore[arg-type]
            model=BasicResponse,
            operation_name="session stop",
        )


def test_parse_session_response_model_rejects_blank_operation_name():
    with pytest.raises(
        HyperbrowserError, match="operation_name must be a non-empty string"
    ):
        parse_session_response_model(
            {"success": True},
            model=BasicResponse,
            operation_name="   ",
        )


def test_parse_session_response_model_wraps_invalid_payloads():
    with pytest.raises(
        HyperbrowserError, match="Failed to parse session stop response"
    ) as exc_info:
        parse_session_response_model(
            {},
            model=BasicResponse,
            operation_name="session stop",
        )

    assert exc_info.value.original_error is not None


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


def test_parse_session_recordings_response_data_wraps_unreadable_recording_items():
    class _BrokenRecordingMapping(Mapping[str, object]):
        def __iter__(self) -> Iterator[str]:
            raise RuntimeError("cannot iterate recording object")

        def __len__(self) -> int:
            return 1

        def __getitem__(self, key: str) -> object:
            _ = key
            return "ignored"

    with pytest.raises(
        HyperbrowserError,
        match="Failed to read session recording object at index 0",
    ) as exc_info:
        parse_session_recordings_response_data([_BrokenRecordingMapping()])

    assert exc_info.value.original_error is not None


def test_parse_session_recordings_response_data_preserves_hyperbrowser_recording_read_errors():
    class _BrokenRecordingMapping(Mapping[str, object]):
        def __iter__(self) -> Iterator[str]:
            raise HyperbrowserError("custom recording read failure")

        def __len__(self) -> int:
            return 1

        def __getitem__(self, key: str) -> object:
            _ = key
            return "ignored"

    with pytest.raises(
        HyperbrowserError, match="custom recording read failure"
    ) as exc_info:
        parse_session_recordings_response_data([_BrokenRecordingMapping()])

    assert exc_info.value.original_error is None


def test_parse_session_recordings_response_data_rejects_non_string_recording_keys():
    with pytest.raises(
        HyperbrowserError,
        match="Expected session recording object keys to be strings at index 0",
    ):
        parse_session_recordings_response_data(
            [
                {1: "bad-key"},  # type: ignore[dict-item]
            ]
        )


def test_parse_session_recordings_response_data_rejects_string_subclass_recording_keys():
    class _Key(str):
        pass

    with pytest.raises(
        HyperbrowserError,
        match="Expected session recording object keys to be strings at index 0",
    ):
        parse_session_recordings_response_data(
            [
                {_Key("type"): "bad-key"},
            ]
        )


def test_parse_session_recordings_response_data_wraps_recording_value_read_failures():
    class _BrokenValueLookupMapping(Mapping[str, object]):
        def __iter__(self) -> Iterator[str]:
            yield "type"

        def __len__(self) -> int:
            return 1

        def __getitem__(self, key: str) -> object:
            _ = key
            raise RuntimeError("cannot read recording value")

    with pytest.raises(
        HyperbrowserError,
        match="Failed to read session recording object value for key 'type' at index 0",
    ) as exc_info:
        parse_session_recordings_response_data([_BrokenValueLookupMapping()])

    assert exc_info.value.original_error is not None


def test_parse_session_recordings_response_data_sanitizes_recording_value_keys():
    class _BrokenValueLookupMapping(Mapping[str, object]):
        def __iter__(self) -> Iterator[str]:
            yield "bad\tkey"

        def __len__(self) -> int:
            return 1

        def __getitem__(self, key: str) -> object:
            _ = key
            raise RuntimeError("cannot read recording value")

    with pytest.raises(
        HyperbrowserError,
        match=(
            "Failed to read session recording object value "
            "for key 'bad\\?key' at index 0"
        ),
    ) as exc_info:
        parse_session_recordings_response_data([_BrokenValueLookupMapping()])

    assert exc_info.value.original_error is not None


def test_parse_session_recordings_response_data_rejects_string_subclass_recording_keys_before_value_reads():
    class _BrokenKey(str):
        def __iter__(self):
            raise RuntimeError("cannot iterate recording key")

    class _BrokenValueLookupMapping(Mapping[str, object]):
        def __iter__(self) -> Iterator[str]:
            yield _BrokenKey("type")

        def __len__(self) -> int:
            return 1

        def __getitem__(self, key: str) -> object:
            _ = key
            raise RuntimeError("cannot read recording value")

    with pytest.raises(
        HyperbrowserError,
        match="Expected session recording object keys to be strings at index 0",
    ) as exc_info:
        parse_session_recordings_response_data([_BrokenValueLookupMapping()])

    assert exc_info.value.original_error is None


def test_parse_session_recordings_response_data_preserves_hyperbrowser_value_read_errors():
    class _BrokenValueLookupMapping(Mapping[str, object]):
        def __iter__(self) -> Iterator[str]:
            yield "type"

        def __len__(self) -> int:
            return 1

        def __getitem__(self, key: str) -> object:
            _ = key
            raise HyperbrowserError("custom recording value read failure")

    with pytest.raises(
        HyperbrowserError, match="custom recording value read failure"
    ) as exc_info:
        parse_session_recordings_response_data([_BrokenValueLookupMapping()])

    assert exc_info.value.original_error is None


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


def test_sync_session_manager_stop_rejects_invalid_payload_shapes():
    manager = SyncSessionManager(_FakeClient(_SyncTransport(["invalid"])))

    with pytest.raises(
        HyperbrowserError, match="Expected session stop response to be an object"
    ):
        manager.stop("session_123")


def test_async_session_manager_get_recording_rejects_invalid_payload_shapes():
    manager = AsyncSessionManager(_FakeClient(_AsyncTransport({"bad": "payload"})))

    async def run():
        with pytest.raises(
            HyperbrowserError,
            match="Expected session recording response to be a list of objects",
        ):
            await manager.get_recording("session_123")

    asyncio.run(run())


def test_async_session_manager_stop_rejects_invalid_payload_shapes():
    manager = AsyncSessionManager(_FakeClient(_AsyncTransport(["invalid"])))

    async def run():
        with pytest.raises(
            HyperbrowserError, match="Expected session stop response to be an object"
        ):
            await manager.stop("session_123")

    asyncio.run(run())
