from hyperbrowser.client.managers.polling_defaults import (
    DEFAULT_POLLING_RETRY_ATTEMPTS,
    DEFAULT_POLLING_RETRY_DELAY_SECONDS,
)
from hyperbrowser.models.consts import POLLING_ATTEMPTS


def test_polling_defaults_use_sdk_polling_attempts_constant():
    assert DEFAULT_POLLING_RETRY_ATTEMPTS == POLLING_ATTEMPTS


def test_polling_defaults_retry_delay_constant_is_expected_value():
    assert DEFAULT_POLLING_RETRY_DELAY_SECONDS == 0.5
