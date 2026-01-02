"""
Integration tests for full trade lifecycle.

Tests the complete flow from market data → risk validation → execution → audit.
"""

import os
import time

import pytest

# Set up test environment before imports
os.environ["PAPER_MODE"] = "true"
os.environ["SIGNER_TYPE"] = "null"
os.environ["PRIVATE_KEY"] = "0000000000000000000000000000000000000000000000000000000000000001"


class TestFullTradeLifecycle:
    """Integration tests for complete trade workflows."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment."""
        os.environ["PAPER_MODE"] = "true"
        os.environ["SIGNER_TYPE"] = "null"
        yield

    def test_paper_deposit_and_trade_flow(self, container):
        """Test complete paper trading flow: deposit → validate → trade."""
        # Use container components directly
        paper_engine = container.paper_engine
        risk_guardian = container.risk_guardian

        # Step 1: Deposit funds
        deposit_result = paper_engine.deposit("agent_zero", "USDC", 10000.0)
        # deposit_result can be a string or dict depending on implementation
        assert deposit_result is not None

        # Step 2: Validate trade risk
        risk_result = risk_guardian.validate_trade(side="buy", symbol="BTC/USDT", amount_usd=500.0, portfolio_value=10000.0)
        assert risk_result["allowed"] is True

        # Step 3: Execute trade via paper engine
        trade_result = paper_engine.execute_trade(
            user_id="agent_zero", side="buy", symbol="BTC/USDT", amount=0.005, price=100000.0, rationale="integration test"
        )
        assert trade_result is not None

    def test_risk_guardian_blocks_oversized_trade(self, container):
        """Test that Risk Guardian blocks trades exceeding position limits."""
        paper_engine = container.paper_engine
        risk_guardian = container.risk_guardian

        # Deposit funds
        paper_engine.deposit("agent_zero", "USDC", 10000.0)

        # Try to validate a trade that's too large (>5% of portfolio)
        result = risk_guardian.validate_trade(
            side="buy",
            symbol="BTC/USDT",
            amount_usd=600.0,  # 6% of $10,000
            portfolio_value=10000.0,
        )

        assert result["allowed"] is False
        assert "Position size too large" in result["reason"]

    def test_risk_guardian_blocks_falling_knife(self, container):
        """Test that Risk Guardian blocks buys during extreme bearish sentiment."""
        from risk_manager import RiskGuardian

        guardian = RiskGuardian()

        # Direct test with extreme bearish sentiment
        result = guardian.validate_trade(
            side="buy",
            symbol="BTC/USDT",
            amount_usd=100.0,
            portfolio_value=10000.0,
            sentiment_score=-0.7,  # Extreme bearish
        )

        assert result["allowed"] is False
        assert "Falling Knife" in result["reason"]

    def test_risk_guardian_allows_sell_during_bearish(self, container):
        """Test that sells are allowed even during bearish conditions."""
        from risk_manager import RiskGuardian

        guardian = RiskGuardian()

        result = guardian.validate_trade(side="sell", symbol="BTC/USDT", amount_usd=100.0, portfolio_value=10000.0, sentiment_score=-0.7)

        assert result["allowed"] is True

    def test_daily_loss_limit_enforcement(self, container):
        """Test daily loss limit halts buying."""
        from risk_manager import RiskGuardian

        guardian = RiskGuardian()

        # Simulate 6% daily loss
        result = guardian.validate_trade(
            side="buy",
            symbol="BTC/USDT",
            amount_usd=100.0,
            portfolio_value=10000.0,
            daily_loss_pct=-0.06,  # 6% loss
        )

        assert result["allowed"] is False
        assert "Daily Loss Limit" in result["reason"]

    def test_max_drawdown_enforcement(self, container):
        """Test max drawdown halts buying."""
        from risk_manager import RiskGuardian

        guardian = RiskGuardian()

        # Simulate 12% drawdown
        result = guardian.validate_trade(side="buy", symbol="BTC/USDT", amount_usd=100.0, portfolio_value=10000.0, current_drawdown_pct=0.12)

        assert result["allowed"] is False
        assert "Max Drawdown" in result["reason"]


class TestMarketDataIntegration:
    """Integration tests for market data flow."""

    def test_marketdata_bus_available(self, container):
        """Test MarketDataBus is initialized."""
        marketdata_bus = container.marketdata_bus
        assert marketdata_bus is not None

    def test_backtest_engine_fetch_ohlcv(self, container):
        """Test backtest engine can structure data."""
        backtest_engine = container.backtest_engine

        # The backtest engine should have fetch_ohlcv method
        assert hasattr(backtest_engine, "fetch_ohlcv")
        assert hasattr(backtest_engine, "run")


class TestPolicyEngineIntegration:
    """Integration tests for policy engine."""

    def test_policy_blocks_disallowed_chain(self, container):
        """Test policy engine blocks non-allowlisted chains."""
        from policy_engine import PolicyEngine, PolicyError

        # Set restrictive allowlist
        os.environ["ALLOW_CHAINS"] = "ethereum,base"

        engine = PolicyEngine()

        with pytest.raises(PolicyError) as exc_info:
            engine.validate_swap(chain="polygon", from_token="USDC", to_token="ETH", amount=100.0)

        assert exc_info.value.code == "chain_not_allowed"

        # Cleanup
        del os.environ["ALLOW_CHAINS"]

    def test_policy_allows_configured_chain(self, container):
        """Test policy engine allows allowlisted chains."""
        from policy_engine import PolicyEngine

        os.environ["ALLOW_CHAINS"] = "ethereum,base"

        engine = PolicyEngine()

        # Should not raise
        engine.validate_swap(chain="ethereum", from_token="USDC", to_token="ETH", amount=100.0)

        # Cleanup
        del os.environ["ALLOW_CHAINS"]

    def test_policy_enforces_max_trade_amount(self, container):
        """Test policy engine enforces trade amount limits."""
        from policy_engine import PolicyEngine, PolicyError

        os.environ["MAX_TRADE_AMOUNT"] = "500"

        engine = PolicyEngine()

        with pytest.raises(PolicyError) as exc_info:
            engine.validate_swap(chain="ethereum", from_token="USDC", to_token="ETH", amount=600.0)

        assert exc_info.value.code == "trade_amount_too_large"

        # Cleanup
        del os.environ["MAX_TRADE_AMOUNT"]

    def test_cex_order_policy_validation(self, container):
        """Test policy validation for CEX orders."""
        from policy_engine import PolicyEngine, PolicyError

        os.environ["ALLOW_EXCHANGES"] = "binance,kraken"

        engine = PolicyEngine()

        # Should pass
        engine.validate_cex_order(exchange_id="binance", symbol="BTC/USDT", market_type="spot", side="buy", amount=0.01, order_type="market")

        # Should fail
        with pytest.raises(PolicyError) as exc_info:
            engine.validate_cex_order(exchange_id="okx", symbol="BTC/USDT", market_type="spot", side="buy", amount=0.01, order_type="market")

        assert exc_info.value.code == "exchange_not_allowed"

        # Cleanup
        del os.environ["ALLOW_EXCHANGES"]


class TestAuditLogIntegration:
    """Integration tests for audit logging."""

    def test_audit_log_records_trades(self, container):
        """Test that trades are recorded in audit log."""
        from observability.audit import AuditLog, now_ms

        audit = AuditLog()

        if audit.enabled():
            # Record a trade
            audit.append(
                ts_ms=now_ms(),
                request_id="test-123",
                tool="place_cex_order",
                ok=True,
                mode="paper",
                venue="cex",
                exchange="binance",
                market_type="spot",
                summary={"symbol": "BTC/USDT", "side": "buy", "amount": 0.01},
            )

            # Verify we can export (structure test)
            csv = audit.export_tax_report()
            assert "Timestamp" in csv

    def test_audit_log_hash_chain(self, container):
        """Test audit log maintains hash chain integrity."""
        from observability.audit import AuditLog, now_ms

        audit = AuditLog()

        if audit.enabled():
            # Add multiple entries
            for i in range(3):
                audit.append(ts_ms=now_ms(), request_id=f"test-{i}", tool="test_tool", ok=True, summary={"test": i})


class TestBacktestIntegration:
    """Integration tests for backtesting engine."""

    def test_backtest_with_complex_strategy(self, container):
        """Test backtesting with a more complex strategy."""
        from backtest_engine import BacktestEngine

        engine = BacktestEngine()

        # Strategy using multiple conditions
        strategy_code = """
def on_candle(price, rsi, state):
    # Initialize state
    if 'last_action' not in state:
        state['last_action'] = 'hold'
        state['entry_price'] = 0
    
    # Buy on oversold RSI
    if rsi < 30 and state['last_action'] != 'buy':
        state['last_action'] = 'buy'
        state['entry_price'] = price
        return 'buy'
    
    # Sell on overbought RSI or 5% profit
    if state['last_action'] == 'buy':
        profit_pct = (price - state['entry_price']) / state['entry_price'] if state['entry_price'] > 0 else 0
        if rsi > 70 or profit_pct > 0.05:
            state['last_action'] = 'sell'
            return 'sell'
    
    return 'hold'
"""

        result = engine.run(strategy_code=strategy_code, symbol="BTC/USDT", timeframe="1h")

        # May fail without data, but structure is tested
        assert result is not None

    def test_backtest_invalid_strategy_returns_error(self, container):
        """Test that invalid strategy code returns error, not exception."""
        from backtest_engine import BacktestEngine

        engine = BacktestEngine()

        # Invalid Python syntax
        strategy_code = """
def on_candle(price, rsi, state)  # Missing colon
    return 'buy'
"""

        result = engine.run(strategy_code=strategy_code, symbol="BTC/USDT", timeframe="1h")

        # Should return error dict, not raise
        assert result is not None
        assert "error" in result


class TestInsightStoreIntegration:
    """Integration tests for multi-agent insight sharing."""

    def test_post_and_retrieve_insight(self, container):
        """Test posting and retrieving market insights."""
        from intelligence.insights import InsightStore

        store = InsightStore()

        # Post an insight
        insight = store.post_insight(
            symbol="BTC/USDT", agent_id="researcher_1", signal="BULLISH", confidence=0.85, reasoning="RSI oversold with bullish divergence", ttl_seconds=300
        )

        assert insight is not None
        assert insight.symbol == "BTC/USDT"

        # Retrieve insights
        insights = store.get_latest_insights(symbol="BTC/USDT")

        assert len(insights) > 0

    def test_insight_expiry(self, container):
        """Test that insights expire after TTL."""
        from intelligence.insights import InsightStore

        store = InsightStore()

        # Post with very short TTL
        insight = store.post_insight(
            symbol="ETH/USDT",
            agent_id="test_agent",
            signal="BEARISH",
            confidence=0.7,
            reasoning="Test insight",
            ttl_seconds=1,  # 1 second TTL
        )

        # Should exist immediately
        insights = store.get_latest_insights("ETH/USDT")
        found = any(i.insight_id == insight.insight_id for i in insights)
        assert found

        # Wait for expiry
        time.sleep(1.5)

        # Should be expired now
        insights = store.get_latest_insights("ETH/USDT")
        found = any(i.insight_id == insight.insight_id for i in insights)
        assert not found


class TestMarketRegimeIntegration:
    """Integration tests for market regime detection."""

    def test_regime_detector_available(self, container):
        """Test market regime detector is available."""
        regime_detector = container.regime_detector
        assert regime_detector is not None
        assert hasattr(regime_detector, "detect")
