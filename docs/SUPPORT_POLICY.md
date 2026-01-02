# Support Policy

This document defines the support status of ReadyTrader-Crypto components.

______________________________________________________________________

## Support Tiers

### Tier 1: Fully Supported

Production-ready components with full test coverage and documentation.

| Component          | Status    | Notes                                        |
| :----------------- | :-------- | :------------------------------------------- |
| Paper Trading      | Supported | Full order lifecycle, risk guardian, metrics |
| CEX: Binance       | Supported | Spot + futures, WebSocket streams            |
| CEX: Kraken        | Supported | Spot, native WebSocket                       |
| CEX: Coinbase      | Supported | Spot, native WebSocket                       |
| DEX: Uniswap V3    | Supported | Ethereum, Base, Arbitrum, Optimism           |
| DEX: 1inch Router  | Supported | Multi-chain aggregation                      |
| Signer: Keystore   | Supported | AES-256-CTR encrypted JSON keystore          |
| Signer: EnvKey     | Supported | Environment variable private key             |
| MCP Server (stdio) | Supported | Agent Zero, Claude Desktop                   |
| FastAPI Server     | Supported | WebSocket + REST API                         |
| Risk Guardian      | Supported | Position sizing, drawdown, sentiment         |

### Tier 2: Experimental

Working components that may have edge cases or limited testing.

| Component        | Status       | Notes                                |
| :--------------- | :----------- | :----------------------------------- |
| CEX: Bybit       | Experimental | Basic spot support, untested futures |
| CEX: OKX         | Experimental | Basic support via CCXT               |
| DEX: Aave V3     | Experimental | Lending/borrowing                    |
| Signer: Remote   | Experimental | HTTP-based remote signer             |
| Signer: CB-MPC   | Experimental | Coinbase 2-party MPC                 |
| PostgreSQL Store | Experimental | Multi-instance persistence           |
| Redis Store      | Experimental | High-performance caching             |

### Tier 3: Community / Unsupported

Contributed or legacy components with no active maintenance.

| Component       | Status      | Notes                         |
| :-------------- | :---------- | :---------------------------- |
| Other CEX (50+) | Community   | May work via CCXT, not tested |
| Solana DEX      | Unsupported | Not implemented               |
| Cross-chain     | Unsupported | Not implemented               |

______________________________________________________________________

## Tool Support Matrix

### Fully Supported Tools

| Tool                      | Paper | Live CEX | Live DEX | Notes                  |
| :------------------------ | :---- | :------- | :------- | :--------------------- |
| `get_crypto_price`        | ✓     | ✓        | ✓        | MarketDataBus routing  |
| `fetch_ohlcv`             | ✓     | ✓        | ✓        | CCXT historical data   |
| `get_sentiment`           | ✓     | ✓        | ✓        | Fear & Greed Index     |
| `get_news`                | ✓     | ✓        | ✓        | RSS aggregation        |
| `get_free_news`           | ✓     | ✓        | ✓        | Public RSS feeds       |
| `get_market_regime`       | ✓     | ✓        | ✓        | ADX-based detection    |
| `validate_trade_risk`     | ✓     | ✓        | ✓        | Risk guardian checks   |
| `deposit_paper_funds`     | ✓     | N/A      | N/A      | Paper mode only        |
| `place_cex_order`         | ✓     | ✓        | N/A      | Full lifecycle support |
| `get_cex_balance`         | ✓     | ✓        | N/A      | Account balances       |
| `swap_tokens`             | ✓     | N/A      | ✓        | 1inch aggregation      |
| `transfer_eth`            | N/A   | N/A      | ✓        | Native transfers       |
| `run_backtest_simulation` | ✓     | ✓        | ✓        | Sandboxed execution    |

### Experimental Tools

| Tool                   | Status       | Notes                      |
| :--------------------- | :----------- | :------------------------- |
| `get_social_sentiment` | Experimental | Requires API keys          |
| `get_financial_news`   | Experimental | Requires NewsAPI key       |
| `start_cex_private_ws` | Experimental | Exchange-dependent support |

______________________________________________________________________

## Deprecation Policy

### Version Numbering

ReadyTrader-Crypto uses semantic versioning (SemVer):

- **MAJOR** (X.0.0): Breaking changes to tool signatures or behavior
- **MINOR** (0.X.0): New features, backward-compatible changes
- **PATCH** (0.0.X): Bug fixes, documentation updates

### Breaking Changes

A breaking change is any modification that:

1. Removes or renames a tool
1. Changes required parameters of a tool
1. Changes the response structure of a tool
1. Changes error codes or their meanings
1. Removes or changes environment variable names

### Deprecation Timeline

1. **Announcement**: Deprecated features are marked in CHANGELOG.md
1. **Warning Period**: 2 minor versions minimum
1. **Removal**: In the next major version

### Migration Guides

Breaking changes will include migration guides in:

- CHANGELOG.md (summary)
- Dedicated migration doc if complex

______________________________________________________________________

## API Stability

### Stable APIs

These interfaces are stable and follow the deprecation policy:

- MCP tool signatures
- FastAPI REST endpoints
- WebSocket message formats
- Environment variable names
- Error code prefixes

### Internal APIs

These may change without notice:

- Python module internal functions (prefixed with `_`)
- Test utilities
- Build scripts

______________________________________________________________________

## Getting Help

### Documentation

1. [docs/README.md](README.md) - Documentation index
1. [docs/ERRORS.md](ERRORS.md) - Error troubleshooting
1. [RUNBOOK.md](../RUNBOOK.md) - Operator runbook

### Issue Reporting

For bugs and feature requests:

1. Check existing issues
1. Provide reproducible steps
1. Include version number (`settings.VERSION`)
1. Include relevant logs (redact secrets)

### Security Issues

Report security vulnerabilities via:

- [SECURITY.md](../SECURITY.md) process
- Do NOT create public issues for security bugs
