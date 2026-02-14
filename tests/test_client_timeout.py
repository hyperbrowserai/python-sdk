import asyncio
from decimal import Decimal
import math
from fractions import Fraction

import pytest

import hyperbrowser.client.timeout_utils as timeout_helpers
from hyperbrowser import AsyncHyperbrowser, Hyperbrowser
from hyperbrowser.exceptions import HyperbrowserError


def test_sync_client_rejects_negative_timeout():
    with pytest.raises(HyperbrowserError, match="timeout must be non-negative"):
        Hyperbrowser(api_key="test-key", timeout=-1)


def test_async_client_rejects_negative_timeout():
    with pytest.raises(HyperbrowserError, match="timeout must be non-negative"):
        AsyncHyperbrowser(api_key="test-key", timeout=-1)


def test_sync_client_accepts_none_timeout():
    client = Hyperbrowser(api_key="test-key", timeout=None)
    client.close()


def test_async_client_accepts_none_timeout():
    async def run() -> None:
        client = AsyncHyperbrowser(api_key="test-key", timeout=None)
        await client.close()

    asyncio.run(run())


def test_sync_client_normalizes_fraction_timeout_to_float():
    client = Hyperbrowser(
        api_key="test-key",
        timeout=Fraction(1, 2),  # type: ignore[arg-type]
    )
    try:
        assert isinstance(client.transport.client.timeout.connect, float)
        assert client.transport.client.timeout.connect == 0.5
    finally:
        client.close()


def test_async_client_normalizes_fraction_timeout_to_float():
    async def run() -> None:
        client = AsyncHyperbrowser(
            api_key="test-key",
            timeout=Fraction(1, 2),  # type: ignore[arg-type]
        )
        try:
            assert isinstance(client.transport.client.timeout.connect, float)
            assert client.transport.client.timeout.connect == 0.5
        finally:
            await client.close()

    asyncio.run(run())


def test_sync_client_normalizes_decimal_timeout_to_float():
    client = Hyperbrowser(
        api_key="test-key",
        timeout=Decimal("0.5"),  # type: ignore[arg-type]
    )
    try:
        assert isinstance(client.transport.client.timeout.connect, float)
        assert client.transport.client.timeout.connect == 0.5
    finally:
        client.close()


def test_async_client_normalizes_decimal_timeout_to_float():
    async def run() -> None:
        client = AsyncHyperbrowser(
            api_key="test-key",
            timeout=Decimal("0.5"),  # type: ignore[arg-type]
        )
        try:
            assert isinstance(client.transport.client.timeout.connect, float)
            assert client.transport.client.timeout.connect == 0.5
        finally:
            await client.close()

    asyncio.run(run())


def test_sync_client_rejects_non_numeric_timeout():
    with pytest.raises(HyperbrowserError, match="timeout must be a number"):
        Hyperbrowser(api_key="test-key", timeout="30")  # type: ignore[arg-type]


def test_async_client_rejects_non_numeric_timeout():
    with pytest.raises(HyperbrowserError, match="timeout must be a number"):
        AsyncHyperbrowser(api_key="test-key", timeout="30")  # type: ignore[arg-type]


def test_sync_client_rejects_boolean_timeout():
    with pytest.raises(HyperbrowserError, match="timeout must be a number"):
        Hyperbrowser(api_key="test-key", timeout=True)


def test_async_client_rejects_boolean_timeout():
    with pytest.raises(HyperbrowserError, match="timeout must be a number"):
        AsyncHyperbrowser(api_key="test-key", timeout=False)


@pytest.mark.parametrize("invalid_timeout", [math.inf, -math.inf, math.nan])
def test_sync_client_rejects_non_finite_timeout(invalid_timeout: float):
    with pytest.raises(HyperbrowserError, match="timeout must be finite"):
        Hyperbrowser(api_key="test-key", timeout=invalid_timeout)


@pytest.mark.parametrize("invalid_timeout", [math.inf, -math.inf, math.nan])
def test_async_client_rejects_non_finite_timeout(invalid_timeout: float):
    with pytest.raises(HyperbrowserError, match="timeout must be finite"):
        AsyncHyperbrowser(api_key="test-key", timeout=invalid_timeout)


def test_sync_client_rejects_overflowing_real_timeout():
    with pytest.raises(HyperbrowserError, match="timeout must be finite") as exc_info:
        Hyperbrowser(api_key="test-key", timeout=Fraction(10**1000, 1))

    assert exc_info.value.original_error is not None


def test_async_client_rejects_overflowing_real_timeout():
    with pytest.raises(HyperbrowserError, match="timeout must be finite") as exc_info:
        AsyncHyperbrowser(api_key="test-key", timeout=Fraction(10**1000, 1))

    assert exc_info.value.original_error is not None


def test_sync_client_wraps_timeout_isfinite_failures(
    monkeypatch: pytest.MonkeyPatch,
):
    def _raise_isfinite_error(value: float) -> bool:
        _ = value
        raise OverflowError("finite check overflow")

    monkeypatch.setattr(timeout_helpers.math, "isfinite", _raise_isfinite_error)

    with pytest.raises(HyperbrowserError, match="timeout must be finite") as exc_info:
        Hyperbrowser(api_key="test-key", timeout=1)

    assert exc_info.value.original_error is not None


def test_async_client_wraps_timeout_isfinite_failures(
    monkeypatch: pytest.MonkeyPatch,
):
    def _raise_isfinite_error(value: float) -> bool:
        _ = value
        raise OverflowError("finite check overflow")

    monkeypatch.setattr(timeout_helpers.math, "isfinite", _raise_isfinite_error)

    with pytest.raises(HyperbrowserError, match="timeout must be finite") as exc_info:
        AsyncHyperbrowser(api_key="test-key", timeout=1)

    assert exc_info.value.original_error is not None


def test_sync_client_wraps_unexpected_timeout_float_conversion_failures(
):
    class _BrokenDecimal(Decimal):
        def __float__(self) -> float:
            raise RuntimeError("unexpected float conversion failure")

    with pytest.raises(HyperbrowserError, match="timeout must be finite") as exc_info:
        Hyperbrowser(
            api_key="test-key",
            timeout=_BrokenDecimal("1"),  # type: ignore[arg-type]
        )

    assert isinstance(exc_info.value.original_error, RuntimeError)


def test_async_client_wraps_unexpected_timeout_float_conversion_failures(
):
    class _BrokenDecimal(Decimal):
        def __float__(self) -> float:
            raise RuntimeError("unexpected float conversion failure")

    with pytest.raises(HyperbrowserError, match="timeout must be finite") as exc_info:
        AsyncHyperbrowser(
            api_key="test-key",
            timeout=_BrokenDecimal("1"),  # type: ignore[arg-type]
        )

    assert isinstance(exc_info.value.original_error, RuntimeError)


def test_sync_client_wraps_unexpected_timeout_isfinite_runtime_failures(
    monkeypatch: pytest.MonkeyPatch,
):
    def _raise_isfinite_error(_value: float) -> bool:
        raise RuntimeError("unexpected finite check failure")

    monkeypatch.setattr(timeout_helpers.math, "isfinite", _raise_isfinite_error)

    with pytest.raises(HyperbrowserError, match="timeout must be finite") as exc_info:
        Hyperbrowser(api_key="test-key", timeout=1)

    assert isinstance(exc_info.value.original_error, RuntimeError)


def test_async_client_wraps_unexpected_timeout_isfinite_runtime_failures(
    monkeypatch: pytest.MonkeyPatch,
):
    def _raise_isfinite_error(_value: float) -> bool:
        raise RuntimeError("unexpected finite check failure")

    monkeypatch.setattr(timeout_helpers.math, "isfinite", _raise_isfinite_error)

    with pytest.raises(HyperbrowserError, match="timeout must be finite") as exc_info:
        AsyncHyperbrowser(api_key="test-key", timeout=1)

    assert isinstance(exc_info.value.original_error, RuntimeError)
