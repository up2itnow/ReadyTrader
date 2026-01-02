"""
Comprehensive tests for PolicyEngine.
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from policy_engine import PolicyEngine, PolicyError


@pytest.fixture
def policy_engine():
    return PolicyEngine()


class TestSwapValidation:
    """Test swap validation rules."""

    def test_swap_validation_passes_without_restrictions(self, policy_engine):
        """Test swap passes when no restrictions are configured."""
        # Should not raise
        policy_engine.validate_swap(chain="ethereum", from_token="USDC", to_token="WETH", amount=100.0)

    def test_swap_blocked_by_chain_allowlist(self, policy_engine):
        """Test swap blocked when chain not in allowlist."""
        with patch.dict(os.environ, {"ALLOW_CHAINS": "ethereum,base"}):
            with pytest.raises(PolicyError) as exc_info:
                policy_engine.validate_swap(chain="polygon", from_token="USDC", to_token="WETH", amount=100.0)
            assert exc_info.value.code == "chain_not_allowed"

    def test_swap_blocked_by_token_allowlist(self, policy_engine):
        """Test swap blocked when token not in allowlist."""
        with patch.dict(os.environ, {"ALLOW_TOKENS": "usdc,weth,btc"}):
            with pytest.raises(PolicyError) as exc_info:
                policy_engine.validate_swap(
                    chain="ethereum",
                    from_token="SHIB",  # Not in allowlist
                    to_token="WETH",
                    amount=100.0,
                )
            assert exc_info.value.code == "token_not_allowed"

    def test_swap_blocked_by_max_trade_amount(self, policy_engine):
        """Test swap blocked when amount exceeds MAX_TRADE_AMOUNT."""
        with patch.dict(os.environ, {"MAX_TRADE_AMOUNT": "1000"}):
            with pytest.raises(PolicyError) as exc_info:
                policy_engine.validate_swap(chain="ethereum", from_token="USDC", to_token="WETH", amount=2000.0)
            assert exc_info.value.code == "trade_amount_too_large"

    def test_swap_blocked_by_token_specific_limit(self, policy_engine):
        """Test swap blocked by token-specific limit."""
        with patch.dict(os.environ, {"MAX_TRADE_AMOUNT_USDC": "500"}):
            with pytest.raises(PolicyError) as exc_info:
                policy_engine.validate_swap(chain="ethereum", from_token="USDC", to_token="WETH", amount=600.0)
            assert exc_info.value.code == "trade_amount_too_large"

    def test_swap_uses_overrides(self, policy_engine):
        """Test that overrides take precedence over env vars."""
        with patch.dict(os.environ, {"MAX_TRADE_AMOUNT": "1000"}):
            # Override allows higher limit
            policy_engine.validate_swap(chain="ethereum", from_token="USDC", to_token="WETH", amount=2000.0, overrides={"MAX_TRADE_AMOUNT": 5000.0})


class TestTransferNativeValidation:
    """Test native transfer validation rules."""

    def test_transfer_passes_without_restrictions(self, policy_engine):
        """Test transfer passes when no restrictions configured."""
        policy_engine.validate_transfer_native(chain="ethereum", to_address="0x742d35Cc6634C0532925a3b844Bc9e7595f1E123", amount=1.0)

    def test_transfer_blocked_by_chain_allowlist(self, policy_engine):
        """Test transfer blocked when chain not in allowlist."""
        with patch.dict(os.environ, {"ALLOW_CHAINS": "ethereum"}):
            with pytest.raises(PolicyError) as exc_info:
                policy_engine.validate_transfer_native(chain="arbitrum", to_address="0x742d35Cc6634C0532925a3b844Bc9e7595f1E123", amount=1.0)
            assert exc_info.value.code == "chain_not_allowed"

    def test_transfer_blocked_by_max_amount(self, policy_engine):
        """Test transfer blocked when amount exceeds MAX_TRANSFER_NATIVE."""
        with patch.dict(os.environ, {"MAX_TRANSFER_NATIVE": "0.5"}):
            with pytest.raises(PolicyError) as exc_info:
                policy_engine.validate_transfer_native(chain="ethereum", to_address="0x742d35Cc6634C0532925a3b844Bc9e7595f1E123", amount=1.0)
            assert exc_info.value.code == "transfer_amount_too_large"

    def test_transfer_blocked_by_recipient_allowlist(self, policy_engine):
        """Test transfer blocked when recipient not in allowlist."""
        with patch.dict(os.environ, {"ALLOW_TO_ADDRESSES": "0xAllowed1,0xAllowed2"}):
            with pytest.raises(PolicyError) as exc_info:
                policy_engine.validate_transfer_native(chain="ethereum", to_address="0xNotAllowed", amount=1.0)
            assert exc_info.value.code == "recipient_not_allowed"


class TestSignerValidation:
    """Test signer-related validation."""

    def test_signer_address_passes_without_allowlist(self, policy_engine):
        """Test signer address passes when no allowlist configured."""
        policy_engine.validate_signer_address(address="0x742d35Cc6634C0532925a3b844Bc9e7595f1E123")

    def test_signer_address_blocked_by_allowlist(self, policy_engine):
        """Test signer address blocked when not in allowlist."""
        with patch.dict(os.environ, {"ALLOW_SIGNER_ADDRESSES": "0xAllowed1,0xAllowed2"}):
            with pytest.raises(PolicyError) as exc_info:
                policy_engine.validate_signer_address(address="0x742d35Cc6634C0532925a3b844Bc9e7595f1E123")
            assert exc_info.value.code == "signer_address_not_allowed"


class TestSignTxValidation:
    """Test transaction signing validation."""

    def test_sign_tx_passes_without_restrictions(self, policy_engine):
        """Test sign_tx passes when no restrictions configured."""
        policy_engine.validate_sign_tx(
            chain_id=1,
            to_address="0x742d35Cc6634C0532925a3b844Bc9e7595f1E123",
            value_wei=1000000000000000000,  # 1 ETH
            gas=21000,
            gas_price_wei=20000000000,
            data_hex="0x",
        )

    def test_sign_tx_blocked_by_chain_id_allowlist(self, policy_engine):
        """Test sign_tx blocked when chain_id not in allowlist."""
        with patch.dict(os.environ, {"ALLOW_SIGN_CHAIN_IDS": "1,8453"}):
            with pytest.raises(PolicyError) as exc_info:
                policy_engine.validate_sign_tx(
                    chain_id=42161,  # Arbitrum, not in list
                    to_address="0x742d35Cc6634C0532925a3b844Bc9e7595f1E123",
                    value_wei=0,
                    gas=21000,
                    gas_price_wei=20000000000,
                    data_hex="0x",
                )
            assert exc_info.value.code == "sign_chain_id_not_allowed"

    def test_sign_tx_blocked_by_value_limit(self, policy_engine):
        """Test sign_tx blocked when value exceeds MAX_SIGN_VALUE_WEI."""
        with patch.dict(os.environ, {"MAX_SIGN_VALUE_WEI": "1000000000000000000"}):  # 1 ETH
            with pytest.raises(PolicyError) as exc_info:
                policy_engine.validate_sign_tx(
                    chain_id=1,
                    to_address="0x742d35Cc6634C0532925a3b844Bc9e7595f1E123",
                    value_wei=2000000000000000000,  # 2 ETH
                    gas=21000,
                    gas_price_wei=20000000000,
                    data_hex="0x",
                )
            assert exc_info.value.code == "sign_value_too_large"

    def test_sign_tx_blocked_by_gas_limit(self, policy_engine):
        """Test sign_tx blocked when gas exceeds MAX_SIGN_GAS."""
        with patch.dict(os.environ, {"MAX_SIGN_GAS": "100000"}):
            with pytest.raises(PolicyError) as exc_info:
                policy_engine.validate_sign_tx(
                    chain_id=1,
                    to_address="0x742d35Cc6634C0532925a3b844Bc9e7595f1E123",
                    value_wei=0,
                    gas=500000,  # Exceeds limit
                    gas_price_wei=20000000000,
                    data_hex="0x",
                )
            assert exc_info.value.code == "sign_gas_too_large"

    def test_sign_tx_blocked_by_data_size_limit(self, policy_engine):
        """Test sign_tx blocked when data exceeds MAX_SIGN_DATA_BYTES."""
        with patch.dict(os.environ, {"MAX_SIGN_DATA_BYTES": "100"}):
            large_data = "0x" + "aa" * 200  # 200 bytes
            with pytest.raises(PolicyError) as exc_info:
                policy_engine.validate_sign_tx(
                    chain_id=1, to_address="0x742d35Cc6634C0532925a3b844Bc9e7595f1E123", value_wei=0, gas=21000, gas_price_wei=20000000000, data_hex=large_data
                )
            assert exc_info.value.code == "sign_data_too_large"

    def test_sign_tx_blocks_contract_creation(self, policy_engine):
        """Test sign_tx blocks contract creation when disallowed."""
        with patch.dict(os.environ, {"DISALLOW_SIGN_CONTRACT_CREATION": "true"}):
            with pytest.raises(PolicyError) as exc_info:
                policy_engine.validate_sign_tx(
                    chain_id=1,
                    to_address=None,  # Contract creation
                    value_wei=0,
                    gas=500000,
                    gas_price_wei=20000000000,
                    data_hex="0x608060...",
                )
            assert exc_info.value.code == "sign_contract_creation_not_allowed"


class TestCexOrderValidation:
    """Test CEX order validation."""

    def test_cex_order_passes_valid_params(self, policy_engine):
        """Test CEX order passes with valid parameters."""
        policy_engine.validate_cex_order(exchange_id="binance", symbol="BTC/USDT", market_type="spot", side="buy", amount=0.01, order_type="market")

    def test_cex_order_blocked_by_exchange_allowlist(self, policy_engine):
        """Test CEX order blocked when exchange not in allowlist."""
        with patch.dict(os.environ, {"ALLOW_EXCHANGES": "binance,kraken"}):
            with pytest.raises(PolicyError) as exc_info:
                policy_engine.validate_cex_order(
                    exchange_id="ftx",  # Not in allowlist
                    symbol="BTC/USDT",
                    market_type="spot",
                    side="buy",
                    amount=0.01,
                    order_type="market",
                )
            assert exc_info.value.code == "exchange_not_allowed"

    def test_cex_order_blocked_invalid_side(self, policy_engine):
        """Test CEX order blocked with invalid side."""
        with pytest.raises(PolicyError) as exc_info:
            policy_engine.validate_cex_order(
                exchange_id="binance",
                symbol="BTC/USDT",
                market_type="spot",
                side="hold",  # Invalid
                amount=0.01,
                order_type="market",
            )
        assert exc_info.value.code == "invalid_side"

    def test_cex_order_blocked_invalid_order_type(self, policy_engine):
        """Test CEX order blocked with invalid order type."""
        with pytest.raises(PolicyError) as exc_info:
            policy_engine.validate_cex_order(
                exchange_id="binance",
                symbol="BTC/USDT",
                market_type="spot",
                side="buy",
                amount=0.01,
                order_type="stop_loss",  # Not supported
            )
        assert exc_info.value.code == "invalid_order_type"

    def test_cex_order_blocked_zero_amount(self, policy_engine):
        """Test CEX order blocked with zero amount."""
        with pytest.raises(PolicyError) as exc_info:
            policy_engine.validate_cex_order(
                exchange_id="binance",
                symbol="BTC/USDT",
                market_type="spot",
                side="buy",
                amount=0,  # Invalid
                order_type="market",
            )
        assert exc_info.value.code == "invalid_amount"

    def test_cex_limit_order_requires_price(self, policy_engine):
        """Test CEX limit order requires price."""
        with pytest.raises(PolicyError) as exc_info:
            policy_engine.validate_cex_order(
                exchange_id="binance",
                symbol="BTC/USDT",
                market_type="spot",
                side="buy",
                amount=0.01,
                order_type="limit",
                price=None,  # Missing price
            )
        assert exc_info.value.code == "invalid_price"


class TestInsightBacking:
    """Test insight backing validation for trades."""

    def test_insight_backing_returns_confidence(self, policy_engine):
        """Test valid insight backing returns confidence score."""
        import time

        from intelligence.insights import MarketInsight

        insight = MarketInsight(
            insight_id="test123",
            symbol="BTC/USDT",
            agent_id="agent_zero",
            signal="bullish",
            confidence=0.85,
            reasoning="Technical breakout",
            timestamp_ms=int(time.time() * 1000),
            expires_at_ms=int((time.time() + 3600) * 1000),
            meta={},
        )

        conf = policy_engine.validate_insight_backing(symbol="BTC/USDT", insight_id="test123", insights=[insight])

        assert conf == 0.85

    def test_insight_backing_not_found(self, policy_engine):
        """Test insight not found raises error."""
        with pytest.raises(PolicyError) as exc_info:
            policy_engine.validate_insight_backing(symbol="BTC/USDT", insight_id="nonexistent", insights=[])
        assert exc_info.value.code == "insight_not_found"
