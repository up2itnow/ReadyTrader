"""
Comprehensive tests for PaperTradingEngine.
"""

from __future__ import annotations

import pytest

from paper_engine import PaperTradingEngine


@pytest.fixture
def temp_paper_engine(tmp_path):
    """Create a temporary paper trading engine."""
    db_path = str(tmp_path / "paper.db")
    return PaperTradingEngine(db_path=db_path)


class TestDeposit:
    """Test deposit functionality."""

    def test_deposit_creates_balance(self, temp_paper_engine):
        """Test depositing creates initial balance."""
        result = temp_paper_engine.deposit("user1", "USDT", 10000.0)

        assert "Deposited 10000" in result
        assert temp_paper_engine.get_balance("user1", "USDT") == 10000.0

    def test_deposit_adds_to_existing_balance(self, temp_paper_engine):
        """Test depositing adds to existing balance."""
        temp_paper_engine.deposit("user1", "USDT", 10000.0)
        temp_paper_engine.deposit("user1", "USDT", 5000.0)

        assert temp_paper_engine.get_balance("user1", "USDT") == 15000.0

    def test_deposit_negative_reduces_balance(self, temp_paper_engine):
        """Test negative deposit reduces balance."""
        temp_paper_engine.deposit("user1", "USDT", 10000.0)
        temp_paper_engine.deposit("user1", "USDT", -3000.0)

        assert temp_paper_engine.get_balance("user1", "USDT") == 7000.0


class TestExecuteTrade:
    """Test trade execution functionality."""

    def test_buy_trade_success(self, temp_paper_engine):
        """Test successful buy trade."""
        temp_paper_engine.deposit("user1", "USDT", 10000.0)

        result = temp_paper_engine.execute_trade(user_id="user1", side="buy", symbol="BTC/USDT", amount=0.1, price=50000.0, rationale="Test buy")

        assert "Paper Trade Executed" in result
        assert "BUY" in result
        assert temp_paper_engine.get_balance("user1", "USDT") == 5000.0  # 10000 - 5000
        assert temp_paper_engine.get_balance("user1", "BTC") == 0.1

    def test_sell_trade_success(self, temp_paper_engine):
        """Test successful sell trade."""
        temp_paper_engine.deposit("user1", "BTC", 1.0)

        result = temp_paper_engine.execute_trade(user_id="user1", side="sell", symbol="BTC/USDT", amount=0.5, price=50000.0, rationale="Test sell")

        assert "Paper Trade Executed" in result
        assert "SELL" in result
        assert temp_paper_engine.get_balance("user1", "BTC") == 0.5
        assert temp_paper_engine.get_balance("user1", "USDT") == 25000.0

    def test_buy_insufficient_funds(self, temp_paper_engine):
        """Test buy with insufficient funds."""
        temp_paper_engine.deposit("user1", "USDT", 1000.0)

        result = temp_paper_engine.execute_trade(user_id="user1", side="buy", symbol="BTC/USDT", amount=1.0, price=50000.0, rationale="Test")

        assert "Insufficient fund" in result

    def test_sell_insufficient_funds(self, temp_paper_engine):
        """Test sell with insufficient funds."""
        temp_paper_engine.deposit("user1", "BTC", 0.1)

        result = temp_paper_engine.execute_trade(user_id="user1", side="sell", symbol="BTC/USDT", amount=1.0, price=50000.0, rationale="Test")

        assert "Insufficient fund" in result


class TestLimitOrders:
    """Test limit order functionality."""

    def test_place_limit_buy_order(self, temp_paper_engine):
        """Test placing limit buy order."""
        temp_paper_engine.deposit("user1", "USDT", 10000.0)

        result = temp_paper_engine.place_limit_order(user_id="user1", side="buy", symbol="BTC/USDT", amount=0.1, price=45000.0)

        assert "Order Placed" in result
        assert "BUY" in result
        # Funds should be locked (deducted)
        assert temp_paper_engine.get_balance("user1", "USDT") == 5500.0  # 10000 - 4500

    def test_place_limit_sell_order(self, temp_paper_engine):
        """Test placing limit sell order."""
        temp_paper_engine.deposit("user1", "BTC", 1.0)

        result = temp_paper_engine.place_limit_order(user_id="user1", side="sell", symbol="BTC/USDT", amount=0.5, price=55000.0)

        assert "Order Placed" in result
        assert "SELL" in result
        # Funds should be locked
        assert temp_paper_engine.get_balance("user1", "BTC") == 0.5

    def test_check_orders_fills_buy(self, temp_paper_engine):
        """Test buy order fills when price drops."""
        temp_paper_engine.deposit("user1", "USDT", 10000.0)
        temp_paper_engine.place_limit_order("user1", "buy", "BTC/USDT", 0.1, 45000.0)

        # Price drops to limit, order should fill
        filled = temp_paper_engine.check_open_orders("BTC/USDT", 44000.0)

        assert len(filled) == 1
        assert "FILLED" in filled[0]
        assert "BUY" in filled[0]
        # User should now have BTC
        assert temp_paper_engine.get_balance("user1", "BTC") == 0.1

    def test_check_orders_fills_sell(self, temp_paper_engine):
        """Test sell order fills when price rises."""
        temp_paper_engine.deposit("user1", "BTC", 1.0)
        temp_paper_engine.place_limit_order("user1", "sell", "BTC/USDT", 0.5, 55000.0)

        # Price rises to limit, order should fill
        filled = temp_paper_engine.check_open_orders("BTC/USDT", 56000.0)

        assert len(filled) == 1
        assert "FILLED" in filled[0]
        assert "SELL" in filled[0]
        # User should now have USDT
        assert temp_paper_engine.get_balance("user1", "USDT") == 27500.0  # 0.5 * 55000


class TestRiskMetrics:
    """Test risk metrics calculation."""

    def test_risk_metrics_initial_zero(self, temp_paper_engine):
        """Test risk metrics start at zero."""
        metrics = temp_paper_engine.get_risk_metrics("user1")

        assert metrics["daily_pnl_pct"] == 0.0
        assert metrics["drawdown_pct"] == 0.0

    def test_risk_metrics_with_trades(self, temp_paper_engine):
        """Test risk metrics calculate after trades."""
        temp_paper_engine.deposit("user1", "USDC", 10000.0)
        temp_paper_engine.execute_trade("user1", "buy", "BTC/USDC", 0.1, 50000.0, "test")

        metrics = temp_paper_engine.get_risk_metrics("user1")

        assert "daily_pnl_pct" in metrics
        assert "drawdown_pct" in metrics
        assert metrics["drawdown_pct"] >= 0.0


class TestPortfolioValue:
    """Test portfolio value calculation."""

    def test_portfolio_value_stablecoins(self, temp_paper_engine):
        """Test portfolio value with stablecoins only."""
        temp_paper_engine.deposit("user1", "USDT", 5000.0)
        temp_paper_engine.deposit("user1", "USDC", 5000.0)

        value = temp_paper_engine.get_portfolio_value_usd("user1")

        assert value == 10000.0

    def test_portfolio_value_with_assets(self, temp_paper_engine):
        """Test portfolio value with traded assets."""
        temp_paper_engine.deposit("user1", "USDC", 10000.0)
        temp_paper_engine.execute_trade("user1", "buy", "BTC/USDC", 0.1, 50000.0, "test")

        # BTC price should be cached at 50000
        value = temp_paper_engine.get_portfolio_value_usd("user1")

        # 5000 USDC + 0.1 BTC @ $50000 = 5000 + 5000 = 10000
        assert value == 10000.0


class TestWalletReset:
    """Test wallet reset functionality."""

    def test_reset_clears_balances(self, temp_paper_engine):
        """Test reset clears all balances."""
        temp_paper_engine.deposit("user1", "USDT", 10000.0)
        temp_paper_engine.deposit("user1", "BTC", 1.0)

        result = temp_paper_engine.reset_wallet("user1")

        assert "reset" in result.lower()
        assert temp_paper_engine.get_balance("user1", "USDT") == 0.0
        assert temp_paper_engine.get_balance("user1", "BTC") == 0.0


class TestGetBalances:
    """Test balance retrieval."""

    def test_get_balance_empty(self, temp_paper_engine):
        """Test get balance for non-existent user."""
        balance = temp_paper_engine.get_balance("nonexistent", "USDT")
        assert balance == 0.0

    def test_get_balance_multiple_assets(self, temp_paper_engine):
        """Test getting balances for multiple assets."""
        temp_paper_engine.deposit("user1", "USDT", 1000.0)
        temp_paper_engine.deposit("user1", "BTC", 0.5)
        temp_paper_engine.deposit("user1", "ETH", 10.0)

        assert temp_paper_engine.get_balance("user1", "USDT") == 1000.0
        assert temp_paper_engine.get_balance("user1", "BTC") == 0.5
        assert temp_paper_engine.get_balance("user1", "ETH") == 10.0
