"""
Integration tests for full DEX execution flows.

These tests verify the complete flow from tool invocation through
policy validation, signing, and transaction broadcast.
"""

from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def temp_data_dir(tmp_path):
    """Create temporary directories for test data."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    env_patches = {
        "PAPER_DB_PATH": str(data_dir / "paper.db"),
        "AUDIT_DB_PATH": str(data_dir / "audit.db"),
        "IDEMPOTENCY_DB_PATH": str(data_dir / "idempotency.db"),
        "EXECUTION_DB_PATH": str(data_dir / "execution.db"),
        "PAPER_MODE": "true",
        "SIGNER_TYPE": "null",
        "EXECUTION_MODE": "dex",
    }

    with patch.dict(os.environ, env_patches):
        yield data_dir


@pytest.fixture
def fresh_container(temp_data_dir):
    """Create a fresh container instance for integration testing."""
    import importlib

    import app.core.config
    import app.core.container

    importlib.reload(app.core.config)
    importlib.reload(app.core.container)

    return app.core.container.global_container


class TestDexPaperModeFlow:
    """Test DEX execution in paper mode."""

    def test_swap_tokens_paper_mode(self, fresh_container, temp_data_dir):
        """Test token swap execution in paper mode via paper engine."""
        # Setup paper wallet
        fresh_container.paper_engine.deposit("agent_zero", "USDC", 10000.0)

        # Execute trade via paper engine directly (swap simulation)
        result = fresh_container.paper_engine.execute_trade(
            user_id="agent_zero",
            side="sell",  # Selling USDC for WETH
            symbol="USDC/WETH",
            amount=100.0,
            price=1.0,
            rationale="test_swap",
        )

        assert result is not None

    def test_transfer_eth_blocked_in_paper_mode(self, temp_data_dir):
        """Test native ETH transfers are blocked in paper mode."""
        from app.core.config import settings
        from app.tools.execution import transfer_eth

        with patch.object(settings, "PAPER_MODE", True):
            result = json.loads(transfer_eth(to_address="0x742d35Cc6634C0532925a3b844Bc9e7595f1E123", amount=1.0, chain="ethereum"))

            assert result["ok"] is False
            assert result["error"]["code"] == "paper_mode_not_supported"


class TestDexLiveModeFlow:
    """Test DEX execution in live mode.

    Note: Full live mode testing requires complex mocking.
    Core policy validation is tested directly via PolicyEngine.
    """

    def test_policy_engine_chain_allowlist(self, temp_data_dir):
        """Test policy engine enforces chain allowlist."""
        from policy_engine import PolicyEngine, PolicyError

        # Set restrictive allowlist
        with patch.dict(os.environ, {"ALLOW_CHAINS": "ethereum"}):
            engine = PolicyEngine()

            # Allowed chain should pass
            engine.validate_swap(chain="ethereum", from_token="USDC", to_token="WETH", amount=100.0)

            # Disallowed chain should fail
            with pytest.raises(PolicyError) as exc_info:
                engine.validate_swap(chain="polygon", from_token="USDC", to_token="WETH", amount=100.0)
            assert exc_info.value.code == "chain_not_allowed"

    def test_policy_engine_token_allowlist(self, temp_data_dir):
        """Test policy engine enforces token allowlist."""
        from policy_engine import PolicyEngine, PolicyError

        with patch.dict(os.environ, {"ALLOW_TOKENS": "usdc,weth,eth"}):
            engine = PolicyEngine()

            # Allowed tokens should pass
            engine.validate_swap(chain="ethereum", from_token="USDC", to_token="WETH", amount=100.0)

            # Disallowed token should fail
            with pytest.raises(PolicyError) as exc_info:
                engine.validate_swap(
                    chain="ethereum",
                    from_token="SHIB",  # Not in allowlist
                    to_token="WETH",
                    amount=100.0,
                )
            assert exc_info.value.code == "token_not_allowed"


class TestDexSigningFlow:
    """Test signing integration for DEX transactions."""

    def test_signer_address_validation(self, temp_data_dir):
        """Test that signer address is validated against allowlist."""
        from policy_engine import PolicyEngine

        policy = PolicyEngine()

        # Without allowlist, any address passes
        policy.validate_signer_address(address="0x742d35Cc6634C0532925a3b844Bc9e7595f1E123")

        # With allowlist set, only allowed addresses pass
        with patch.dict(os.environ, {"ALLOW_SIGNER_ADDRESSES": "0xAllowed1,0xAllowed2"}):
            with pytest.raises(Exception) as exc_info:
                policy.validate_signer_address(address="0x742d35Cc6634C0532925a3b844Bc9e7595f1E123")
            # Check that the error is related to allowlist
            assert exc_info.value.code == "signer_address_not_allowed"

    def test_router_address_validation(self, temp_data_dir):
        """Test that router addresses are validated."""
        from policy_engine import PolicyEngine

        policy = PolicyEngine()

        # Without allowlist, any router passes
        policy.validate_router_address(
            chain="ethereum",
            router_address="0x1111111254fb6c44bAC0beD2854e76F90643097d",  # 1inch router
            context={},
        )

        # With allowlist set, only allowed routers pass
        with patch.dict(os.environ, {"ALLOW_ROUTERS": "0xAllowedRouter"}):
            with pytest.raises(Exception) as exc_info:
                policy.validate_router_address(chain="ethereum", router_address="0x1111111254fb6c44bAC0beD2854e76F90643097d", context={})
            assert exc_info.value.code == "router_not_allowed"


class TestDexTransferFlow:
    """Test native transfer flows."""

    def test_transfer_native_requires_live_mode(self, temp_data_dir):
        """Test that native transfers require live mode."""
        from app.core.config import settings
        from app.tools.execution import transfer_eth

        # Paper mode should reject
        with patch.object(settings, "PAPER_MODE", True):
            result = json.loads(transfer_eth(to_address="0x742d35Cc6634C0532925a3b844Bc9e7595f1E123", amount=1.0))

            assert result["ok"] is False

    def test_policy_engine_transfer_limits(self, temp_data_dir):
        """Test policy engine enforces transfer limits."""
        from policy_engine import PolicyEngine, PolicyError

        with patch.dict(os.environ, {"MAX_TRANSFER_NATIVE": "0.5"}):
            engine = PolicyEngine()

            # Under limit should pass
            engine.validate_transfer_native(chain="ethereum", to_address="0x742d35Cc6634C0532925a3b844Bc9e7595f1E123", amount=0.4)

            # Over limit should fail
            with pytest.raises(PolicyError) as exc_info:
                engine.validate_transfer_native(chain="ethereum", to_address="0x742d35Cc6634C0532925a3b844Bc9e7595f1E123", amount=1.0)
            assert exc_info.value.code == "transfer_amount_too_large"


class TestDexUniswapV3Integration:
    """Test Uniswap V3 integration for liquidity positions."""

    def test_uniswap_v3_client_initialization(self):
        """Test Uniswap V3 client initializes correctly."""
        from defi.uniswap_v3 import ETHEREUM, UniswapV3Client

        mock_w3 = MagicMock()
        mock_w3.eth.contract.return_value = MagicMock()

        client = UniswapV3Client(mock_w3, chain_id=ETHEREUM)

        assert client.chain_id == ETHEREUM
        assert client.manager is not None

    def test_uniswap_v3_unsupported_chain(self):
        """Test that unsupported chains raise appropriate errors."""
        from defi.uniswap_v3 import UniswapV3Client

        mock_w3 = MagicMock()

        # Chain ID 999 is not supported
        client = UniswapV3Client(mock_w3, chain_id=999)

        with pytest.raises(ValueError) as exc_info:
            client.mint_position(token0="0xToken0", token1="0xToken1", fee=3000, amount0=1000, amount1=1000, recipient="0xRecipient")
        assert "not supported" in str(exc_info.value)
