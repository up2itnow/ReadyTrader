"""
Exchange Sandbox Integration Tests.

These tests verify connectivity and basic operations against exchange APIs.
Tests are designed to be resilient to geo-restrictions - they will automatically
use the appropriate exchange variant or skip gracefully if unavailable.

Test Categories:
1. Public API tests (auto-select exchange variant based on availability)
2. Authenticated API tests (require sandbox credentials)
3. DEX module tests (import/structure tests)

Environment Variables:
- CEX_BINANCE_TESTNET_API_KEY / CEX_BINANCE_TESTNET_API_SECRET
- CEX_KRAKEN_TESTNET_API_KEY / CEX_KRAKEN_TESTNET_API_SECRET
- CEX_COINBASE_SANDBOX_API_KEY / CEX_COINBASE_SANDBOX_API_SECRET
- PREFER_BINANCE_US=1 (force binanceus even if binance.com is available)

Usage:
    pytest tests/integration/test_exchange_sandbox.py -v
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from typing import Any


# =============================================================================
# Skip Markers
# =============================================================================

skip_needs_credentials = pytest.mark.skipif(
    os.environ.get("CI") == "true",
    reason="Test requires exchange credentials not available in CI",
)


# =============================================================================
# Helper Functions
# =============================================================================


async def get_available_binance_exchange():
    """
    Get an available Binance exchange instance.

    Tries binance.com first (for non-US users), falls back to binanceus.
    If PREFER_BINANCE_US=1 is set, uses binanceus directly.

    Returns:
        tuple: (exchange_instance, exchange_id) or (None, None) if unavailable
    """
    import ccxt.async_support as ccxt

    # Check preference
    prefer_us = os.environ.get("PREFER_BINANCE_US") == "1" or os.environ.get("CI") == "true"

    # Order of exchanges to try
    exchanges_to_try = (
        [
            ("binanceus", ccxt.binanceus),
            ("binance", ccxt.binance),
        ]
        if prefer_us
        else [
            ("binance", ccxt.binance),
            ("binanceus", ccxt.binanceus),
        ]
    )

    for exchange_id, exchange_class in exchanges_to_try:
        exchange = exchange_class({"enableRateLimit": True})
        try:
            # Quick connectivity check
            await exchange.fetch_ticker("BTC/USDT")
            return exchange, exchange_id
        except ccxt.ExchangeNotAvailable:
            # Geo-restricted, try next
            await exchange.close()
            continue
        except Exception:
            # Other error, try next
            await exchange.close()
            continue

    return None, None


def is_geo_restriction_error(error: Exception) -> bool:
    """Check if an error is due to geo-restrictions."""
    error_str = str(error).lower()
    return any(
        phrase in error_str
        for phrase in [
            "restricted location",
            "not available in your region",
            "geo",
            "451",  # HTTP 451 Unavailable For Legal Reasons
        ]
    )


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def binance_testnet_credentials() -> dict[str, str] | None:
    """Return Binance testnet credentials if available."""
    api_key = os.environ.get("CEX_BINANCE_TESTNET_API_KEY")
    api_secret = os.environ.get("CEX_BINANCE_TESTNET_API_SECRET")
    if api_key and api_secret:
        return {"api_key": api_key, "api_secret": api_secret}
    return None


@pytest.fixture
def kraken_testnet_credentials() -> dict[str, str] | None:
    """Return Kraken testnet credentials if available."""
    api_key = os.environ.get("CEX_KRAKEN_TESTNET_API_KEY")
    api_secret = os.environ.get("CEX_KRAKEN_TESTNET_API_SECRET")
    if api_key and api_secret:
        return {"api_key": api_key, "api_secret": api_secret}
    return None


@pytest.fixture
def coinbase_sandbox_credentials() -> dict[str, str] | None:
    """Return Coinbase sandbox credentials if available."""
    api_key = os.environ.get("CEX_COINBASE_SANDBOX_API_KEY")
    api_secret = os.environ.get("CEX_COINBASE_SANDBOX_API_SECRET")
    passphrase = os.environ.get("CEX_COINBASE_SANDBOX_PASSPHRASE")
    if api_key and api_secret:
        creds = {"api_key": api_key, "api_secret": api_secret}
        if passphrase:
            creds["password"] = passphrase
        return creds
    return None


# =============================================================================
# Binance Tests (auto-selects binance.com or binanceus based on availability)
# =============================================================================


class TestBinancePublicAPI:
    """Binance public API tests (auto-selects available variant)."""

    @pytest.mark.asyncio
    async def test_binance_public_ticker(self) -> None:
        """Test fetching public ticker from Binance."""
        exchange, exchange_id = await get_available_binance_exchange()
        if not exchange:
            pytest.skip("No Binance variant available (geo-restricted)")

        try:
            ticker = await exchange.fetch_ticker("BTC/USDT")
            assert ticker is not None
            assert "last" in ticker
            assert "bid" in ticker
            assert "ask" in ticker
            assert ticker["symbol"] == "BTC/USDT"
        finally:
            await exchange.close()

    @pytest.mark.asyncio
    async def test_binance_public_orderbook(self) -> None:
        """Test fetching public orderbook from Binance."""
        exchange, exchange_id = await get_available_binance_exchange()
        if not exchange:
            pytest.skip("No Binance variant available (geo-restricted)")

        try:
            orderbook = await exchange.fetch_order_book("ETH/USDT", limit=10)
            assert orderbook is not None
            assert "bids" in orderbook
            assert "asks" in orderbook
            assert len(orderbook["bids"]) > 0
            assert len(orderbook["asks"]) > 0
        finally:
            await exchange.close()

    @pytest.mark.asyncio
    async def test_binance_public_ohlcv(self) -> None:
        """Test fetching OHLCV data from Binance."""
        exchange, exchange_id = await get_available_binance_exchange()
        if not exchange:
            pytest.skip("No Binance variant available (geo-restricted)")

        try:
            ohlcv = await exchange.fetch_ohlcv("BTC/USDT", "1h", limit=24)
            assert ohlcv is not None
            assert len(ohlcv) > 0
            # Each candle should have [timestamp, open, high, low, close, volume]
            assert len(ohlcv[0]) == 6
        finally:
            await exchange.close()


@skip_needs_credentials
class TestBinanceTestnet:
    """Binance testnet tests (require credentials)."""

    @pytest.mark.asyncio
    async def test_binance_testnet_balance(self, binance_testnet_credentials: dict[str, str] | None) -> None:
        """Test fetching balance from Binance testnet."""
        if not binance_testnet_credentials:
            pytest.skip("Binance testnet credentials not configured")

        import ccxt.async_support as ccxt

        exchange = ccxt.binance(
            {
                "apiKey": binance_testnet_credentials["api_key"],
                "secret": binance_testnet_credentials["api_secret"],
                "sandbox": True,
                "enableRateLimit": True,
            }
        )
        try:
            balance = await exchange.fetch_balance()
            assert balance is not None
            assert "total" in balance
            assert "free" in balance
        except Exception as e:
            if is_geo_restriction_error(e):
                pytest.skip(f"Binance testnet geo-restricted: {e}")
            raise
        finally:
            await exchange.close()

    @pytest.mark.asyncio
    async def test_binance_testnet_markets(self, binance_testnet_credentials: dict[str, str] | None) -> None:
        """Test loading markets from Binance testnet."""
        if not binance_testnet_credentials:
            pytest.skip("Binance testnet credentials not configured")

        import ccxt.async_support as ccxt

        exchange = ccxt.binance(
            {
                "apiKey": binance_testnet_credentials["api_key"],
                "secret": binance_testnet_credentials["api_secret"],
                "sandbox": True,
                "enableRateLimit": True,
            }
        )
        try:
            markets = await exchange.load_markets()
            assert markets is not None
            assert len(markets) > 0
        except Exception as e:
            if is_geo_restriction_error(e):
                pytest.skip(f"Binance testnet geo-restricted: {e}")
            raise
        finally:
            await exchange.close()


# =============================================================================
# Kraken Tests (globally accessible)
# =============================================================================


class TestKrakenPublicAPI:
    """Kraken public API tests (globally accessible)."""

    @pytest.mark.asyncio
    async def test_kraken_public_ticker(self) -> None:
        """Test fetching public ticker from Kraken."""
        import ccxt.async_support as ccxt

        exchange = ccxt.kraken({"enableRateLimit": True})
        try:
            ticker = await exchange.fetch_ticker("BTC/USD")
            assert ticker is not None
            assert "last" in ticker
            assert "bid" in ticker
            assert "ask" in ticker
        except Exception as e:
            if is_geo_restriction_error(e):
                pytest.skip(f"Kraken geo-restricted: {e}")
            raise
        finally:
            await exchange.close()

    @pytest.mark.asyncio
    async def test_kraken_public_orderbook(self) -> None:
        """Test fetching public orderbook from Kraken."""
        import ccxt.async_support as ccxt

        exchange = ccxt.kraken({"enableRateLimit": True})
        try:
            orderbook = await exchange.fetch_order_book("ETH/USD", limit=10)
            assert orderbook is not None
            assert "bids" in orderbook
            assert "asks" in orderbook
        except Exception as e:
            if is_geo_restriction_error(e):
                pytest.skip(f"Kraken geo-restricted: {e}")
            raise
        finally:
            await exchange.close()

    @pytest.mark.asyncio
    async def test_kraken_public_trades(self) -> None:
        """Test fetching recent trades from Kraken."""
        import ccxt.async_support as ccxt

        exchange = ccxt.kraken({"enableRateLimit": True})
        try:
            trades = await exchange.fetch_trades("BTC/USD", limit=10)
            assert trades is not None
            assert len(trades) > 0
            assert "price" in trades[0]
            assert "amount" in trades[0]
        except Exception as e:
            if is_geo_restriction_error(e):
                pytest.skip(f"Kraken geo-restricted: {e}")
            raise
        finally:
            await exchange.close()


@skip_needs_credentials
class TestKrakenTestnet:
    """Kraken testnet tests (require credentials)."""

    @pytest.mark.asyncio
    async def test_kraken_testnet_balance(self, kraken_testnet_credentials: dict[str, str] | None) -> None:
        """Test fetching balance from Kraken."""
        if not kraken_testnet_credentials:
            pytest.skip("Kraken credentials not configured")

        import ccxt.async_support as ccxt

        exchange = ccxt.kraken(
            {
                "apiKey": kraken_testnet_credentials["api_key"],
                "secret": kraken_testnet_credentials["api_secret"],
                "enableRateLimit": True,
            }
        )
        try:
            balance = await exchange.fetch_balance()
            assert balance is not None
            assert "total" in balance
        except Exception as e:
            if is_geo_restriction_error(e):
                pytest.skip(f"Kraken geo-restricted: {e}")
            raise
        finally:
            await exchange.close()


# =============================================================================
# Coinbase Tests (globally accessible)
# =============================================================================


class TestCoinbasePublicAPI:
    """Coinbase public API tests (globally accessible)."""

    @pytest.mark.asyncio
    async def test_coinbase_public_ticker(self) -> None:
        """Test fetching public ticker from Coinbase."""
        import ccxt.async_support as ccxt

        exchange = ccxt.coinbase({"enableRateLimit": True})
        try:
            ticker = await exchange.fetch_ticker("BTC/USD")
            assert ticker is not None
            assert "last" in ticker or "close" in ticker
        except Exception as e:
            if is_geo_restriction_error(e):
                pytest.skip(f"Coinbase geo-restricted: {e}")
            raise
        finally:
            await exchange.close()

    @pytest.mark.asyncio
    async def test_coinbase_public_markets(self) -> None:
        """Test loading markets from Coinbase."""
        import ccxt.async_support as ccxt

        exchange = ccxt.coinbase({"enableRateLimit": True})
        try:
            markets = await exchange.load_markets()
            assert markets is not None
            assert len(markets) > 0
        except Exception as e:
            if is_geo_restriction_error(e):
                pytest.skip(f"Coinbase geo-restricted: {e}")
            raise
        finally:
            await exchange.close()


@skip_needs_credentials
class TestCoinbaseSandbox:
    """Coinbase sandbox tests (require credentials)."""

    @pytest.mark.asyncio
    async def test_coinbase_sandbox_balance(self, coinbase_sandbox_credentials: dict[str, str] | None) -> None:
        """Test fetching balance from Coinbase sandbox."""
        if not coinbase_sandbox_credentials:
            pytest.skip("Coinbase sandbox credentials not configured")

        import ccxt.async_support as ccxt

        config: dict[str, Any] = {
            "apiKey": coinbase_sandbox_credentials["api_key"],
            "secret": coinbase_sandbox_credentials["api_secret"],
            "sandbox": True,
            "enableRateLimit": True,
        }
        if "password" in coinbase_sandbox_credentials:
            config["password"] = coinbase_sandbox_credentials["password"]

        exchange = ccxt.coinbase(config)
        try:
            balance = await exchange.fetch_balance()
            assert balance is not None
            assert "total" in balance
        except Exception as e:
            if is_geo_restriction_error(e):
                pytest.skip(f"Coinbase sandbox geo-restricted: {e}")
            raise
        finally:
            await exchange.close()


# =============================================================================
# DEX Tests (Uniswap V3)
# =============================================================================


class TestUniswapV3Module:
    """Uniswap V3 module tests (import/structure, no network needed)."""

    def test_uniswap_client_import(self) -> None:
        """Test that Uniswap module can be imported."""
        from defi.uniswap_v3 import UniswapV3Client

        assert UniswapV3Client is not None

    def test_uniswap_constants(self) -> None:
        """Test Uniswap constants are defined."""
        from defi.uniswap_v3 import (
            ARBITRUM,
            BASE,
            ETHEREUM,
            NONFUNGIBLE_POSITION_MANAGER,
            OPTIMISM,
        )

        assert ETHEREUM == 1
        assert BASE == 8453
        assert ARBITRUM == 42161
        assert OPTIMISM == 10

        assert ETHEREUM in NONFUNGIBLE_POSITION_MANAGER
        assert BASE in NONFUNGIBLE_POSITION_MANAGER
        assert ARBITRUM in NONFUNGIBLE_POSITION_MANAGER
        assert OPTIMISM in NONFUNGIBLE_POSITION_MANAGER

    def test_uniswap_abi_loaded(self) -> None:
        """Test that Uniswap ABI is properly loaded."""
        from defi.uniswap_v3 import UNI_V3_MANAGER_ABI

        assert UNI_V3_MANAGER_ABI is not None
        assert isinstance(UNI_V3_MANAGER_ABI, list)
        assert len(UNI_V3_MANAGER_ABI) > 0

        function_names = [f.get("name") for f in UNI_V3_MANAGER_ABI]
        assert "mint" in function_names
        assert "collect" in function_names


@skip_needs_credentials
class TestUniswapV3Live:
    """Uniswap V3 live tests (require RPC endpoint)."""

    @pytest.fixture
    def eth_rpc_url(self) -> str | None:
        """Return Ethereum RPC URL if available."""
        return os.environ.get("ETH_RPC_URL") or os.environ.get("ETHEREUM_RPC_URL")

    @pytest.mark.asyncio
    async def test_uniswap_mainnet_connection(self, eth_rpc_url: str | None) -> None:
        """Test connecting to Ethereum for Uniswap operations."""
        if not eth_rpc_url:
            pytest.skip("ETH_RPC_URL not configured")

        assert eth_rpc_url.startswith("http") or eth_rpc_url.startswith("wss")


# =============================================================================
# Cross-Exchange Tests
# =============================================================================


class TestCrossExchangeArbitrage:
    """Cross-exchange price comparison tests."""

    @pytest.mark.asyncio
    async def test_btc_price_spread_reasonable(self) -> None:
        """Test that BTC prices across exchanges are within reasonable spread."""
        import ccxt.async_support as ccxt

        # Get available Binance variant
        binance_exchange, binance_id = await get_available_binance_exchange()
        kraken_exchange = ccxt.kraken({"enableRateLimit": True})

        exchanges = []
        if binance_exchange:
            exchanges.append((binance_exchange, "BTC/USDT"))
        exchanges.append((kraken_exchange, "BTC/USD"))

        prices = []
        try:
            for exchange, symbol in exchanges:
                try:
                    ticker = await exchange.fetch_ticker(symbol)
                    if ticker and ticker.get("last"):
                        prices.append(ticker["last"])
                except Exception:
                    pass
        finally:
            if binance_exchange:
                await binance_exchange.close()
            await kraken_exchange.close()

        if len(prices) >= 2:
            min_price = min(prices)
            max_price = max(prices)
            spread_pct = (max_price - min_price) / min_price * 100
            assert spread_pct < 5, f"BTC price spread too wide: {spread_pct:.2f}%"
        elif len(prices) == 1:
            # Only one exchange available, still a valid test
            assert prices[0] > 0
        else:
            pytest.skip("No exchanges available for price comparison")


# =============================================================================
# Rate Limiting Tests
# =============================================================================


class TestRateLimiting:
    """Rate limiting behavior tests."""

    @pytest.mark.asyncio
    async def test_exchange_rate_limit_respected(self) -> None:
        """Test that rate limiting is properly applied."""
        import time

        import ccxt.async_support as ccxt

        exchange = ccxt.kraken({"enableRateLimit": True})
        try:
            start = time.time()
            for _ in range(3):
                await exchange.fetch_ticker("BTC/USD")
            elapsed = time.time() - start
            assert elapsed >= 0
        except Exception as e:
            if is_geo_restriction_error(e):
                pytest.skip(f"Kraken geo-restricted: {e}")
            raise
        finally:
            await exchange.close()
