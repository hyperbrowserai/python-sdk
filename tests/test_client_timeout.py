import asyncio
from decimal import Decimal
import math
from fractions import Fraction

import pytest

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
    with pytest.raises(HyperbrowserError, match="timeout must be finite"):
        Hyperbrowser(api_key="test-key", timeout=Fraction(10**1000, 1))


def test_async_client_rejects_overflowing_real_timeout():
    with pytest.raises(HyperbrowserError, match="timeout must be finite"):
        AsyncHyperbrowser(api_key="test-key", timeout=Fraction(10**1000, 1))
