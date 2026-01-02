"""
Performance benchmark tests for ReadyTrader-Crypto.

Run with: pytest tests/test_benchmarks.py -v --benchmark-only
Requires: pip install pytest-benchmark
"""

import json
import os
import time
from unittest.mock import patch

import pytest

# Set up test environment
os.environ["PAPER_MODE"] = "true"
os.environ["SIGNER_TYPE"] = "null"
os.environ["PRIVATE_KEY"] = "0000000000000000000000000000000000000000000000000000000000000001"


class TestToolLatencyBenchmarks:
    """Benchmark tests for tool response times."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment."""
        os.environ["PAPER_MODE"] = "true"
        yield

    def test_risk_validation_latency(self, benchmark, container):
        """Benchmark risk validation latency. Target: <50ms."""
        from risk_manager import RiskGuardian

        guardian = RiskGuardian()

        def validate():
            return guardian.validate_trade(
                side="buy", symbol="BTC/USDT", amount_usd=100.0, portfolio_value=10000.0, sentiment_score=0.0, daily_loss_pct=0.0, current_drawdown_pct=0.0
            )

        result = benchmark(validate)
        assert result["allowed"] is True

        # Assert latency target
        assert benchmark.stats.stats.mean < 0.05  # 50ms

    def test_policy_validation_latency(self, benchmark, container):
        """Benchmark policy validation latency. Target: <10ms."""
        from policy_engine import PolicyEngine

        engine = PolicyEngine()

        def validate():
            engine.validate_cex_order(exchange_id="binance", symbol="BTC/USDT", market_type="spot", side="buy", amount=0.01, order_type="market")

        benchmark(validate)
        assert benchmark.stats.stats.mean < 0.01  # 10ms

    def test_paper_order_latency(self, benchmark, container):
        """Benchmark paper order placement latency. Target: <100ms."""
        from app.tools.execution import place_cex_order

        # Initialize paper engine
        from app.tools.trading import deposit_paper_funds

        deposit_paper_funds("USDC", 100000.0)

        def place_order():
            return place_cex_order(symbol="BTC/USDT", side="buy", amount=0.001, order_type="market", exchange="binance")

        result = benchmark(place_order)
        parsed = json.loads(result)
        assert parsed["ok"] is True

        # Assert latency target
        assert benchmark.stats.stats.mean < 0.1  # 100ms

    def test_insight_store_latency(self, benchmark, container):
        """Benchmark insight store operations. Target: <5ms."""
        from intelligence.insights import InsightStore

        store = InsightStore()

        def post_and_get():
            store.post_insight(symbol="BTC/USDT", agent_id="bench_agent", signal="BULLISH", confidence=0.8, reasoning="Test", ttl_seconds=60)
            return store.get_latest_insights("BTC/USDT")

        result = benchmark(post_and_get)
        assert len(result) > 0

        # Assert latency target
        assert benchmark.stats.stats.mean < 0.005  # 5ms

    def test_audit_log_append_latency(self, benchmark, container):
        """Benchmark audit log append latency. Target: <50ms."""
        from observability.audit import AuditLog, now_ms

        audit = AuditLog()

        if not audit.enabled():
            pytest.skip("Audit log not enabled")

        def append():
            audit.append(ts_ms=now_ms(), request_id=f"bench-{time.time()}", tool="benchmark_tool", ok=True, summary={"test": "data"})

        benchmark(append)
        assert benchmark.stats.stats.mean < 0.05  # 50ms


class TestBacktestPerformanceBenchmarks:
    """Benchmark tests for backtest engine performance."""

    def test_backtest_100_candles(self, benchmark, container):
        """Benchmark backtest with 100 candles. Target: <500ms."""
        import numpy as np
        import pandas as pd

        from backtest_engine import BacktestEngine

        engine = BacktestEngine()

        # Create mock data
        dates = pd.date_range(start="2024-01-01", periods=100, freq="h")
        mock_df = pd.DataFrame(
            {
                "timestamp": dates,
                "open": np.random.uniform(90000, 110000, 100),
                "high": np.random.uniform(95000, 115000, 100),
                "low": np.random.uniform(85000, 105000, 100),
                "close": np.random.uniform(90000, 110000, 100),
                "volume": np.random.uniform(100, 1000, 100),
            }
        )

        strategy_code = """
def on_candle(price, rsi, state):
    if rsi < 30:
        return 'buy'
    elif rsi > 70:
        return 'sell'
    return 'hold'
"""

        with patch.object(engine, "fetch_ohlcv", return_value=mock_df):

            def run():
                return engine.run(strategy_code=strategy_code, symbol="BTC/USDT", timeframe="1h")

            result = benchmark(run)
            assert "error" not in result or result.get("error") is None

        # Assert latency target
        assert benchmark.stats.stats.mean < 0.5  # 500ms

    def test_backtest_500_candles(self, benchmark, container):
        """Benchmark backtest with 500 candles. Target: <2s."""
        import numpy as np
        import pandas as pd

        from backtest_engine import BacktestEngine

        engine = BacktestEngine()

        # Create mock data
        dates = pd.date_range(start="2024-01-01", periods=500, freq="h")
        mock_df = pd.DataFrame(
            {
                "timestamp": dates,
                "open": np.random.uniform(90000, 110000, 500),
                "high": np.random.uniform(95000, 115000, 500),
                "low": np.random.uniform(85000, 105000, 500),
                "close": np.random.uniform(90000, 110000, 500),
                "volume": np.random.uniform(100, 1000, 500),
            }
        )

        strategy_code = """
def on_candle(price, rsi, state):
    if rsi < 30:
        return 'buy'
    elif rsi > 70:
        return 'sell'
    return 'hold'
"""

        with patch.object(engine, "fetch_ohlcv", return_value=mock_df):

            def run():
                return engine.run(strategy_code=strategy_code, symbol="BTC/USDT", timeframe="1h")

            result = benchmark(run)
            assert "error" not in result or result.get("error") is None

        # Assert latency target
        assert benchmark.stats.stats.mean < 2.0  # 2s


class TestConcurrencyBenchmarks:
    """Benchmark tests for concurrent operations."""

    def test_concurrent_risk_validations(self, benchmark, container):
        """Benchmark concurrent risk validations."""
        import concurrent.futures

        from risk_manager import RiskGuardian

        guardian = RiskGuardian()

        def validate_many():
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = []
                for i in range(100):
                    futures.append(executor.submit(guardian.validate_trade, side="buy", symbol="BTC/USDT", amount_usd=100.0, portfolio_value=10000.0))

                results = [f.result() for f in futures]
                return results

        results = benchmark(validate_many)
        assert len(results) == 100
        assert all(r["allowed"] for r in results)

    def test_concurrent_policy_validations(self, benchmark, container):
        """Benchmark concurrent policy validations."""
        import concurrent.futures

        from policy_engine import PolicyEngine

        engine = PolicyEngine()

        def validate_many():
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = []
                for i in range(100):
                    futures.append(
                        executor.submit(
                            engine.validate_cex_order,
                            exchange_id="binance",
                            symbol="BTC/USDT",
                            market_type="spot",
                            side="buy",
                            amount=0.01,
                            order_type="market",
                        )
                    )

                # All should succeed (no exceptions)
                for f in futures:
                    f.result()
                return True

        result = benchmark(validate_many)
        assert result is True


class TestMemoryBenchmarks:
    """Benchmark tests for memory usage."""

    def test_insight_store_memory(self, container):
        """Test insight store memory usage with many insights."""
        import tracemalloc

        from intelligence.insights import InsightStore

        tracemalloc.start()

        store = InsightStore()

        # Add many insights
        for i in range(1000):
            store.post_insight(
                symbol=f"TEST{i}/USDT", agent_id="memory_test", signal="BULLISH", confidence=0.5, reasoning="Memory test insight", ttl_seconds=3600
            )

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Assert reasonable memory usage (< 50MB for 1000 insights)
        assert peak < 50 * 1024 * 1024

    def test_paper_engine_memory(self, container):
        """Test paper engine memory usage with many trades."""
        import tracemalloc

        from paper_engine import PaperEngine

        tracemalloc.start()

        engine = PaperEngine()
        engine.deposit("test_agent", "USDC", 1000000.0)

        # Execute many trades
        for i in range(1000):
            engine.execute_trade(
                agent_id="test_agent", side="buy" if i % 2 == 0 else "sell", symbol=f"TEST{i % 10}/USDT", amount=0.01, price=100.0, rationale="Memory test"
            )

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Assert reasonable memory usage (< 100MB for 1000 trades)
        assert peak < 100 * 1024 * 1024


class TestThroughputBenchmarks:
    """Benchmark tests for throughput."""

    def test_risk_validation_throughput(self, container):
        """Test risk validation throughput (validations per second)."""
        import time

        from risk_manager import RiskGuardian

        guardian = RiskGuardian()

        count = 0
        start = time.time()
        duration = 1.0  # Run for 1 second

        while time.time() - start < duration:
            guardian.validate_trade(side="buy", symbol="BTC/USDT", amount_usd=100.0, portfolio_value=10000.0)
            count += 1

        throughput = count / duration

        # Assert minimum throughput (10,000/second is reasonable for in-memory)
        assert throughput > 10000, f"Throughput too low: {throughput}/s"

    def test_policy_validation_throughput(self, container):
        """Test policy validation throughput."""
        import time

        from policy_engine import PolicyEngine

        engine = PolicyEngine()

        count = 0
        start = time.time()
        duration = 1.0

        while time.time() - start < duration:
            engine.validate_cex_order(exchange_id="binance", symbol="BTC/USDT", market_type="spot", side="buy", amount=0.01, order_type="market")
            count += 1

        throughput = count / duration

        # Assert minimum throughput
        assert throughput > 5000, f"Throughput too low: {throughput}/s"


class TestResponseTimeDistribution:
    """Tests for response time distribution analysis."""

    def test_risk_validation_p99_latency(self, container):
        """Test P99 latency for risk validation."""
        import time

        from risk_manager import RiskGuardian

        guardian = RiskGuardian()
        latencies = []

        for _ in range(1000):
            start = time.perf_counter()
            guardian.validate_trade(side="buy", symbol="BTC/USDT", amount_usd=100.0, portfolio_value=10000.0)
            latencies.append(time.perf_counter() - start)

        # Calculate percentiles
        latencies.sort()
        p50 = latencies[500]
        p95 = latencies[950]
        p99 = latencies[990]

        # Assert latency targets (in seconds)
        assert p50 < 0.001, f"P50 too high: {p50 * 1000:.2f}ms"  # 1ms
        assert p95 < 0.005, f"P95 too high: {p95 * 1000:.2f}ms"  # 5ms
        assert p99 < 0.010, f"P99 too high: {p99 * 1000:.2f}ms"  # 10ms
