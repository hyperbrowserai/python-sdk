import pytest

from hyperbrowser.exceptions import HyperbrowserError
from hyperbrowser.transport.async_transport import AsyncTransport
from hyperbrowser.transport.sync import SyncTransport


@pytest.mark.parametrize("transport_class", [SyncTransport, AsyncTransport])
def test_transport_rejects_string_subclass_api_keys(transport_class):
    class _ApiKey(str):
        pass

    with pytest.raises(HyperbrowserError, match="api_key must be a string"):
        transport_class(api_key=_ApiKey("test-key"))


@pytest.mark.parametrize("transport_class", [SyncTransport, AsyncTransport])
def test_transport_rejects_blank_normalized_api_keys(transport_class):
    with pytest.raises(HyperbrowserError, match="api_key must not be empty"):
        transport_class(api_key="   ")
