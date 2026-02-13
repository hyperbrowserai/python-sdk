from hyperbrowser import (
    HyperbrowserError,
    HyperbrowserPollingError,
    HyperbrowserTimeoutError,
    __version__,
)


def test_package_exports_exception_types():
    assert issubclass(HyperbrowserPollingError, HyperbrowserError)
    assert issubclass(HyperbrowserTimeoutError, HyperbrowserError)


def test_package_exports_version_string():
    assert isinstance(__version__, str)
    assert len(__version__) > 0
