import pytest

from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.transport.async_transport import AsyncTransport
from hyperbrowser.transport.sync import SyncTransport


@pytest.mark.parametrize("transport_class", [SyncTransport, AsyncTransport])
def test_transport_wraps_api_key_strip_runtime_errors(transport_class):
    class _BrokenStripApiKey(str):
        def strip(self, chars=None):  # type: ignore[override]
            _ = chars
            raise RuntimeError("api key strip exploded")

    with pytest.raises(HyperbrowserError, match="Failed to normalize api_key") as exc_info:
        transport_class(api_key=_BrokenStripApiKey("test-key"))

    assert isinstance(exc_info.value.original_error, RuntimeError)


@pytest.mark.parametrize("transport_class", [SyncTransport, AsyncTransport])
def test_transport_preserves_hyperbrowser_api_key_strip_errors(transport_class):
    class _BrokenStripApiKey(str):
        def strip(self, chars=None):  # type: ignore[override]
            _ = chars
            raise HyperbrowserError("custom strip failure")

    with pytest.raises(HyperbrowserError, match="custom strip failure") as exc_info:
        transport_class(api_key=_BrokenStripApiKey("test-key"))

    assert exc_info.value.original_error is None


@pytest.mark.parametrize("transport_class", [SyncTransport, AsyncTransport])
def test_transport_wraps_non_string_api_key_strip_results(transport_class):
    class _NonStringStripResultApiKey(str):
        def strip(self, chars=None):  # type: ignore[override]
            _ = chars
            return object()

    with pytest.raises(HyperbrowserError, match="Failed to normalize api_key") as exc_info:
        transport_class(api_key=_NonStringStripResultApiKey("test-key"))

    assert isinstance(exc_info.value.original_error, TypeError)


@pytest.mark.parametrize("transport_class", [SyncTransport, AsyncTransport])
def test_transport_wraps_api_key_character_iteration_failures(transport_class):
    class _BrokenIterApiKey(str):
        def strip(self, chars=None):  # type: ignore[override]
            _ = chars
            return self

        def __iter__(self):
            raise RuntimeError("api key iteration exploded")

    with pytest.raises(
        HyperbrowserError, match="Failed to validate api_key characters"
    ) as exc_info:
        transport_class(api_key=_BrokenIterApiKey("test-key"))

    assert isinstance(exc_info.value.original_error, RuntimeError)


@pytest.mark.parametrize("transport_class", [SyncTransport, AsyncTransport])
def test_transport_wraps_api_key_empty_check_length_failures(transport_class):
    class _BrokenLengthApiKey(str):
        class _NormalizedKey(str):
            def __len__(self):
                raise RuntimeError("api key length exploded")

        def strip(self, chars=None):  # type: ignore[override]
            _ = chars
            return self._NormalizedKey("test-key")

    with pytest.raises(HyperbrowserError, match="Failed to normalize api_key") as exc_info:
        transport_class(api_key=_BrokenLengthApiKey("test-key"))

    assert isinstance(exc_info.value.original_error, RuntimeError)


@pytest.mark.parametrize("transport_class", [SyncTransport, AsyncTransport])
def test_transport_preserves_hyperbrowser_api_key_empty_check_length_failures(
    transport_class,
):
    class _BrokenLengthApiKey(str):
        class _NormalizedKey(str):
            def __len__(self):
                raise HyperbrowserError("custom length failure")

        def strip(self, chars=None):  # type: ignore[override]
            _ = chars
            return self._NormalizedKey("test-key")

    with pytest.raises(HyperbrowserError, match="custom length failure") as exc_info:
        transport_class(api_key=_BrokenLengthApiKey("test-key"))

    assert exc_info.value.original_error is None


@pytest.mark.parametrize("transport_class", [SyncTransport, AsyncTransport])
def test_transport_preserves_hyperbrowser_api_key_character_iteration_failures(
    transport_class,
):
    class _BrokenIterApiKey(str):
        def strip(self, chars=None):  # type: ignore[override]
            _ = chars
            return self

        def __iter__(self):
            raise HyperbrowserError("custom iteration failure")

    with pytest.raises(HyperbrowserError, match="custom iteration failure") as exc_info:
        transport_class(api_key=_BrokenIterApiKey("test-key"))

    assert exc_info.value.original_error is None
