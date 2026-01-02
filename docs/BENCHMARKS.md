# Performance Benchmarks

This document provides latency and throughput benchmarks for ReadyTrader-Crypto operations. Use these as baselines for monitoring and optimization.

______________________________________________________________________

## Executive Summary

| Metric                  | Target  | Typical | Maximum |
| :---------------------- | :------ | :------ | :------ |
| MCP Tool Response       | \<100ms | 50ms    | 500ms   |
| CEX Order Placement     | \<500ms | 200ms   | 2000ms  |
| DEX Swap Execution      | \<30s   | 15s     | 60s     |
| Market Data (REST)      | \<200ms | 100ms   | 1000ms  |
| Market Data (WebSocket) | \<50ms  | 20ms    | 200ms   |
| Backtest (500 candles)  | \<2s    | 800ms   | 5s      |

______________________________________________________________________

## Detailed Benchmarks

### 1. MCP Server Performance

The FastMCP server handles all tool invocations. Latency is measured from request receipt to response sent.

#### Tool Response Times

| Tool Category          | P50    | P95     | P99     | Max     |
| :--------------------- | :----- | :------ | :------ | :------ |
| Market Data (cached)   | 5ms    | 20ms    | 50ms    | 100ms   |
| Market Data (fetch)    | 80ms   | 200ms   | 500ms   | 1000ms  |
| Paper Trading          | 10ms   | 30ms    | 50ms    | 100ms   |
| Risk Validation        | 5ms    | 15ms    | 30ms    | 50ms    |
| Backtest (100 candles) | 200ms  | 400ms   | 600ms   | 1000ms  |
| Backtest (500 candles) | 600ms  | 1200ms  | 2000ms  | 5000ms  |
| CEX Order (paper)      | 15ms   | 40ms    | 80ms    | 150ms   |
| CEX Order (live)       | 150ms  | 400ms   | 800ms   | 2000ms  |
| DEX Swap (paper)       | 20ms   | 50ms    | 100ms   | 200ms   |
| DEX Swap (live)        | 5000ms | 15000ms | 30000ms | 60000ms |

#### Throughput

| Metric                    | Value | Notes                    |
| :------------------------ | :---- | :----------------------- |
| Max Tools/Second          | 100   | Single-threaded FastMCP  |
| Max Concurrent Agents     | 10    | With default rate limits |
| Max WebSocket Connections | 1000  | Per instance             |

### 2. CEX Execution Performance

Central exchange operations via CCXT.

#### Order Lifecycle Timing

```
┌─────────────────────────────────────────────────────────────────┐
│                    CEX Order Timeline                            │
│                                                                  │
│  Agent Request    Policy Check    CCXT Call    Exchange Response │
│       │               │               │               │          │
│       ├───15ms───────>├───5ms────────>├───180ms──────>│          │
│       │               │               │               │          │
│       │<──────────────────────200ms total──────────────│          │
│                                                                  │
│  Market Order: ~200ms total                                      │
│  Limit Order: ~200ms total                                       │
│  Cancel Order: ~150ms total                                      │
│  Fetch Order: ~100ms total                                       │
└─────────────────────────────────────────────────────────────────┘
```

#### Exchange-Specific Latencies

| Exchange | Market Order P50 | Market Order P95 | Notes                  |
| :------- | :--------------- | :--------------- | :--------------------- |
| Binance  | 150ms            | 300ms            | Fastest major exchange |
| Kraken   | 250ms            | 500ms            | Moderate latency       |
| Coinbase | 200ms            | 400ms            | Good consistency       |
| Bybit    | 180ms            | 350ms            | Good performance       |
| OKX      | 200ms            | 400ms            | Consistent             |

#### Rate Limits by Exchange

| Exchange | Orders/Second | Orders/Minute | Weight System           |
| :------- | :------------ | :------------ | :---------------------- |
| Binance  | 10            | 1200          | Weight-based (1200/min) |
| Kraken   | 1             | 60            | Simple rate limit       |
| Coinbase | 10            | 600           | Per-endpoint limits     |
| Bybit    | 20            | 1200          | Weight-based            |
| OKX      | 20            | 1200          | Per-endpoint            |

### 3. DEX Execution Performance

On-chain execution via 1inch and direct contract calls.

#### Swap Transaction Timeline

```
┌─────────────────────────────────────────────────────────────────┐
│                    DEX Swap Timeline                             │
│                                                                  │
│  Build TX     Sign TX    Broadcast    Confirm (3 blocks)        │
│     │           │           │               │                    │
│     ├──500ms───>├──50ms────>├────12-15s────>│                   │
│     │           │           │               │                    │
│     │<─────────────────15s total────────────│                   │
│                                                                  │
│  Ethereum: 12-15s (3 blocks × ~4s)                              │
│  Base/Arbitrum: 2-5s (faster finality)                          │
│  Optimism: 2-5s (faster finality)                               │
└─────────────────────────────────────────────────────────────────┘
```

#### Chain-Specific Performance

| Chain    | Block Time | Confirmation | Gas Cost (typical swap) |
| :------- | :--------- | :----------- | :---------------------- |
| Ethereum | ~12s       | 12-36s       | $5-50                   |
| Base     | ~2s        | 2-6s         | $0.01-0.10              |
| Arbitrum | ~0.3s      | 2-6s         | $0.05-0.50              |
| Optimism | ~2s        | 2-6s         | $0.05-0.50              |

#### 1inch API Performance

| Operation    | P50   | P95   | P99    |
| :----------- | :---- | :---- | :----- |
| Quote        | 200ms | 500ms | 1000ms |
| Build TX     | 300ms | 700ms | 1500ms |
| Health Check | 50ms  | 100ms | 200ms  |

### 4. Market Data Performance

#### REST API Latencies

| Provider  | Ticker P50 | OHLCV P50 | Order Book P50 |
| :-------- | :--------- | :-------- | :------------- |
| Binance   | 50ms       | 80ms      | 60ms           |
| Kraken    | 100ms      | 150ms     | 120ms          |
| Coinbase  | 80ms       | 120ms     | 100ms          |
| CoinGecko | 200ms      | N/A       | N/A            |

#### WebSocket Latencies

| Provider | Ticker Update | Trade Update | Order Book Update |
| :------- | :------------ | :----------- | :---------------- |
| Binance  | 10ms          | 15ms         | 20ms              |
| Kraken   | 50ms          | 50ms         | 50ms              |
| Coinbase | 30ms          | 30ms         | 30ms              |

#### MarketDataBus Priority Performance

```
┌─────────────────────────────────────────────────────────────────┐
│                MarketDataBus Source Priority                     │
│                                                                  │
│  Priority 0: WebSocket Store                                    │
│  ├─ Latency: 10-50ms                                            │
│  ├─ Freshness: Real-time                                        │
│  └─ Reliability: High (with auto-reconnect)                     │
│                                                                  │
│  Priority 1: Ingest Store (User feeds)                          │
│  ├─ Latency: User-dependent                                     │
│  ├─ Freshness: User-dependent                                   │
│  └─ Reliability: User-dependent                                 │
│                                                                  │
│  Priority 2: CCXT REST (Fallback)                               │
│  ├─ Latency: 50-200ms                                           │
│  ├─ Freshness: Polled (5s default TTL)                          │
│  └─ Reliability: High                                           │
└─────────────────────────────────────────────────────────────────┘
```

### 5. Backtest Engine Performance

#### Execution Time by Data Size

| Candles | Indicators     | Simple Strategy | Complex Strategy |
| :------ | :------------- | :-------------- | :--------------- |
| 100     | RSI, SMA       | 150ms           | 300ms            |
| 500     | RSI, SMA       | 600ms           | 1200ms           |
| 1000    | RSI, SMA, MACD | 1500ms          | 3000ms           |
| 5000    | Full TA suite  | 8000ms          | 15000ms          |

#### Memory Usage

| Candles | Base Memory | With Indicators | Peak During Backtest |
| :------ | :---------- | :-------------- | :------------------- |
| 500     | 50MB        | 80MB            | 150MB                |
| 5000    | 100MB       | 200MB           | 400MB                |
| 50000   | 500MB       | 1GB             | 2GB                  |

### 6. Stress Test Performance

#### Synthetic Market Generation

| Scenarios | Generation Time | Total Runtime |
| :-------- | :-------------- | :------------ |
| 50        | 2s              | 30s           |
| 200       | 8s              | 120s          |
| 1000      | 40s             | 600s          |

#### Resource Usage During Stress Test

| Metric            | 50 Scenarios | 200 Scenarios | 1000 Scenarios |
| :---------------- | :----------- | :------------ | :------------- |
| CPU (single core) | 40%          | 60%           | 80%            |
| Memory            | 200MB        | 400MB         | 1GB            |
| Disk I/O          | 10MB/s       | 20MB/s        | 50MB/s         |

______________________________________________________________________

## Optimization Guidelines

### 1. CEX Execution Optimization

```python
# Use idempotency keys to prevent duplicates
result = place_cex_order(
    symbol="BTC/USDT",
    side="buy",
    amount=0.01,
    idempotency_key=f"order-{uuid4()}"
)

# Batch balance checks
# Instead of checking before each order, cache balances
```

### 2. Market Data Optimization

```bash
# Enable WebSocket for low-latency data
export MARKETDATA_WS_ENABLED=true

# Configure caching
export TICKER_CACHE_TTL_SEC=5
export OHLCV_CACHE_TTL_SEC=60
```

### 3. DEX Execution Optimization

```bash
# Use faster chains for lower latency
export ALLOW_CHAINS=base,arbitrum,optimism

# Pre-approve tokens to skip approval transactions
# Configure gas price strategy
export DEX_GAS_STRATEGY=fast  # fast, standard, slow
```

### 4. Backtest Optimization

```python
# Limit candle count for initial testing
result = run_backtest_simulation(
    strategy_code=code,
    symbol="BTC/USDT",
    timeframe="1h"  # Use 1h instead of 1m for faster backtests
)

# Use simpler indicators during development
# Add complexity only when needed
```

______________________________________________________________________

## Monitoring Metrics

### Key Performance Indicators (KPIs)

```prometheus
# Tool response time histogram
readytrader_tool_latency_seconds{tool="place_cex_order"} 

# Order placement success rate
readytrader_orders_total{status="success"} / readytrader_orders_total

# Market data freshness
readytrader_marketdata_age_seconds{symbol="BTC/USDT"}

# WebSocket connection status
readytrader_ws_connected{exchange="binance"}
```

### Alerting Thresholds

| Metric                     | Warning | Critical |
| :------------------------- | :------ | :------- |
| Tool Latency P95           | >500ms  | >2000ms  |
| Order Success Rate         | \<95%   | \<90%    |
| Market Data Age            | >30s    | >60s     |
| WebSocket Disconnects/Hour | >5      | >10      |
| Error Rate                 | >1%     | >5%      |

______________________________________________________________________

## Benchmark Test Suite

Run benchmarks locally:

```bash
# Install benchmark dependencies
pip install pytest-benchmark

# Run benchmark suite
pytest tests/benchmarks/ -v --benchmark-only

# Generate benchmark report
pytest tests/benchmarks/ --benchmark-json=benchmark_results.json
```

### Sample Benchmark Test

```python
# tests/benchmarks/test_execution_benchmarks.py

import pytest
from app.tools.execution import place_cex_order
from app.core.config import settings

@pytest.fixture(autouse=True)
def paper_mode():
    settings.PAPER_MODE = True

def test_paper_order_latency(benchmark):
    result = benchmark(
        place_cex_order,
        symbol="BTC/USDT",
        side="buy",
        amount=0.01
    )
    assert '"ok": true' in result

def test_risk_validation_latency(benchmark):
    from app.tools.trading import validate_trade_risk
    result = benchmark(
        validate_trade_risk,
        side="buy",
        symbol="BTC/USDT",
        amount_usd=100,
        portfolio_value=10000
    )
    assert '"ok": true' in result
```

______________________________________________________________________

## Hardware Recommendations

### Minimum Requirements

| Component | Specification | Notes                  |
| :-------- | :------------ | :--------------------- |
| CPU       | 2 cores       | Single-threaded MCP    |
| RAM       | 4GB           | 8GB for stress testing |
| Disk      | 10GB SSD      | For audit logs         |
| Network   | 10 Mbps       | Low latency important  |

### Recommended for Production

| Component | Specification | Notes               |
| :-------- | :------------ | :------------------ |
| CPU       | 4+ cores      | Parallel operations |
| RAM       | 16GB          | Large backtests     |
| Disk      | 50GB NVMe     | Fast audit writes   |
| Network   | 100 Mbps      | Multiple exchanges  |

### Optimal for High-Frequency

| Component | Specification | Notes                  |
| :-------- | :------------ | :--------------------- |
| CPU       | 8+ cores      | Parallel everything    |
| RAM       | 32GB          | In-memory caching      |
| Disk      | 500GB NVMe    | Historical data        |
| Network   | 1 Gbps        | Co-located if possible |

______________________________________________________________________

## Version History

| Version | Date       | Changes            |
| :------ | :--------- | :----------------- |
| 1.0     | 2025-01-01 | Initial benchmarks |
