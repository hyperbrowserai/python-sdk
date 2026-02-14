import pytest

from hyperbrowser.client.managers.computer_action_utils import (
    normalize_computer_action_endpoint,
)
from hyperbrowser.exceptions import HyperbrowserError


class _SessionWithoutEndpoint:
    pass


class _SessionWithFailingEndpoint:
    @property
    def computer_action_endpoint(self) -> str:
        raise RuntimeError("endpoint unavailable")


class _SessionWithHyperbrowserEndpointFailure:
    @property
    def computer_action_endpoint(self) -> str:
        raise HyperbrowserError("custom endpoint failure")


class _Session:
    def __init__(self, endpoint):
        self.computer_action_endpoint = endpoint


def test_normalize_computer_action_endpoint_returns_valid_value():
    assert (
        normalize_computer_action_endpoint(_Session("https://example.com/action"))
        == "https://example.com/action"
    )


def test_normalize_computer_action_endpoint_wraps_missing_attribute_failures():
    with pytest.raises(
        HyperbrowserError, match="session must include computer_action_endpoint"
    ) as exc_info:
        normalize_computer_action_endpoint(_SessionWithoutEndpoint())

    assert isinstance(exc_info.value.original_error, AttributeError)


def test_normalize_computer_action_endpoint_wraps_runtime_attribute_failures():
    with pytest.raises(
        HyperbrowserError, match="session must include computer_action_endpoint"
    ) as exc_info:
        normalize_computer_action_endpoint(_SessionWithFailingEndpoint())

    assert isinstance(exc_info.value.original_error, RuntimeError)


def test_normalize_computer_action_endpoint_preserves_hyperbrowser_failures():
    with pytest.raises(HyperbrowserError, match="custom endpoint failure") as exc_info:
        normalize_computer_action_endpoint(_SessionWithHyperbrowserEndpointFailure())

    assert exc_info.value.original_error is None


def test_normalize_computer_action_endpoint_rejects_missing_endpoint():
    with pytest.raises(
        HyperbrowserError, match="Computer action endpoint not available for this session"
    ):
        normalize_computer_action_endpoint(_Session(None))


def test_normalize_computer_action_endpoint_rejects_non_string_endpoint():
    with pytest.raises(
        HyperbrowserError, match="session computer_action_endpoint must be a string"
    ):
        normalize_computer_action_endpoint(_Session(123))


def test_normalize_computer_action_endpoint_rejects_string_subclass_endpoint():
    class _EndpointString(str):
        pass

    with pytest.raises(
        HyperbrowserError, match="session computer_action_endpoint must be a string"
    ):
        normalize_computer_action_endpoint(_Session(_EndpointString("https://x.com")))


def test_normalize_computer_action_endpoint_rejects_surrounding_whitespace():
    with pytest.raises(
        HyperbrowserError,
        match="session computer_action_endpoint must not contain leading or trailing whitespace",
    ):
        normalize_computer_action_endpoint(_Session(" https://example.com/action "))


def test_normalize_computer_action_endpoint_rejects_control_characters():
    with pytest.raises(
        HyperbrowserError,
        match="session computer_action_endpoint must not contain control characters",
    ):
        normalize_computer_action_endpoint(_Session("https://example.com/\x07action"))
