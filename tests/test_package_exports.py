from hyperbrowser import (
    HyperbrowserError,
    HyperbrowserPollingError,
    HyperbrowserTimeoutError,
)


def test_package_exports_exception_types():
    assert issubclass(HyperbrowserPollingError, HyperbrowserError)
    assert issubclass(HyperbrowserTimeoutError, HyperbrowserError)
