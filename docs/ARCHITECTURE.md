# ReadyTrader-Crypto Architecture

This document describes the system architecture, component interactions, and data flows in ReadyTrader-Crypto.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AI AGENT LAYER                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   Claude     │  │   Gemini     │  │ Agent Zero   │  │   Custom     │    │
│  │   Desktop    │  │   Agent      │  │              │  │   Agent      │    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    │
│         │                 │                 │                 │             │
│         └─────────────────┴────────┬────────┴─────────────────┘             │
│                                    │                                         │
│                           MCP Protocol (stdio/HTTP)                          │
└────────────────────────────────────┼────────────────────────────────────────┘
                                     │
┌────────────────────────────────────▼────────────────────────────────────────┐
│                         READYTRADER-CRYPTO MCP SERVER                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                           FastMCP Server                             │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │   │
│  │  │Market Data  │ │  Trading    │ │  Research   │ │  Execution  │   │   │
│  │  │   Tools     │ │   Tools     │ │   Tools     │ │   Tools     │   │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│  ┌─────────────────────────────────▼─────────────────────────────────────┐ │
│  │                        SAFETY & GOVERNANCE LAYER                       │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │ │
│  │  │    Risk     │  │   Policy    │  │  Execution  │  │    Rate     │  │ │
│  │  │  Guardian   │  │   Engine    │  │   Store     │  │  Limiter    │  │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘  │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                    │                                         │
│  ┌─────────────────────────────────▼─────────────────────────────────────┐ │
│  │                         EXECUTION LAYER                                │ │
│  │  ┌─────────────────────┐              ┌─────────────────────┐        │ │
│  │  │      CEX Executor    │              │     DEX Handler      │        │ │
│  │  │  ┌───────────────┐  │              │  ┌───────────────┐  │        │ │
│  │  │  │    Binance    │  │              │  │    1inch      │  │        │ │
│  │  │  │    Kraken     │  │              │  │   Uniswap V3  │  │        │ │
│  │  │  │   Coinbase    │  │              │  │    Aave V3    │  │        │ │
│  │  │  │   100+ more   │  │              │  └───────────────┘  │        │ │
│  │  │  └───────────────┘  │              │                      │        │ │
│  │  └─────────────────────┘              └─────────────────────┘        │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                    │                                         │
│  ┌─────────────────────────────────▼─────────────────────────────────────┐ │
│  │                        SIGNING & CUSTODY                               │ │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐         │ │
│  │  │ Env Key   │  │ Keystore  │  │  Remote   │  │ MPC 2PC   │         │ │
│  │  │ Signer    │  │  Signer   │  │  Signer   │  │  Signer   │         │ │
│  │  └───────────┘  └───────────┘  └───────────┘  └───────────┘         │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           EXTERNAL SERVICES                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │  Exchanges  │  │  Blockchains │  │ Data APIs  │  │  Webhooks   │        │
│  │  (CEX/DEX)  │  │  (EVM RPCs)  │  │  (News/Soc)│  │  (Discord)  │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Component Descriptions

### 1. AI Agent Layer

AI agents connect to ReadyTrader-Crypto via the Model Context Protocol (MCP). Supported agents:

- **Claude Desktop**: Anthropic's desktop app with MCP support
- **Agent Zero**: Open-source agent framework
- **Custom Agents**: Any MCP-compatible agent

### 2. MCP Server (FastMCP)

The core server exposes tools organized into categories:

| Category    | Tools                                              | Purpose                           |
| ----------- | -------------------------------------------------- | --------------------------------- |
| Market Data | `get_crypto_price`, `fetch_ohlcv`, `get_sentiment` | Price feeds, historical data      |
| Trading     | `deposit_paper_funds`, `validate_trade_risk`       | Paper trading, risk validation    |
| Research    | `run_backtest_simulation`, `get_market_regime`     | Strategy testing, market analysis |
| Execution   | `place_cex_order`, `swap_tokens`, `transfer_eth`   | Live/paper trade execution        |

### 3. Safety & Governance Layer

```
┌─────────────────────────────────────────────────────────────────┐
│                    Request Flow Through Safety Layer             │
│                                                                  │
│  Agent Request                                                   │
│       │                                                          │
│       ▼                                                          │
│  ┌─────────────┐                                                │
│  │Rate Limiter │──▶ Blocks if rate exceeded                     │
│  └──────┬──────┘                                                │
│         │                                                        │
│         ▼                                                        │
│  ┌─────────────┐                                                │
│  │Risk Guardian│──▶ Validates position size, sentiment, limits  │
│  └──────┬──────┘                                                │
│         │                                                        │
│         ▼                                                        │
│  ┌─────────────┐                                                │
│  │Policy Engine│──▶ Enforces allowlists (chains, tokens, etc.)  │
│  └──────┬──────┘                                                │
│         │                                                        │
│         ▼                                                        │
│  ┌─────────────┐                                                │
│  │Exec. Store  │──▶ Creates approval proposal if approve_each   │
│  └──────┬──────┘                                                │
│         │                                                        │
│         ▼                                                        │
│    Execution                                                     │
└─────────────────────────────────────────────────────────────────┘
```

#### Risk Guardian Rules

| Rule          | Threshold           | Action     |
| ------------- | ------------------- | ---------- |
| Position Size | Max 5% of portfolio | Block      |
| Daily Loss    | Max 5% loss         | Halt buys  |
| Max Drawdown  | 10% from peak       | Halt buys  |
| Falling Knife | Sentiment < -0.5    | Block buys |

#### Policy Engine Allowlists

| Setting   | Environment Variable     | Effect                      |
| --------- | ------------------------ | --------------------------- |
| Chains    | `ALLOW_CHAINS`           | Restrict to specific chains |
| Tokens    | `ALLOW_TOKENS`           | Restrict tradeable tokens   |
| Exchanges | `ALLOW_EXCHANGES`        | Restrict to specific CEXs   |
| Signers   | `ALLOW_SIGNER_ADDRESSES` | Pin expected signer address |

### 4. Execution Layer

#### CEX Execution Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     CEX Order Execution Flow                     │
│                                                                  │
│  place_cex_order(symbol, side, amount)                          │
│       │                                                          │
│       ├──▶ Paper Mode? ──▶ Paper Engine ──▶ Return result       │
│       │                                                          │
│       ▼                                                          │
│  Policy Validation                                               │
│       │                                                          │
│       ├──▶ Approval Required? ──▶ Create Proposal ──▶ Wait      │
│       │                                                          │
│       ▼                                                          │
│  CexExecutor (CCXT)                                             │
│       │                                                          │
│       ├──▶ Symbol Resolution (spot/swap/future)                 │
│       ├──▶ Retry with Exponential Backoff                       │
│       │                                                          │
│       ▼                                                          │
│  Exchange API ──▶ Order Response ──▶ Audit Log                  │
└─────────────────────────────────────────────────────────────────┘
```

#### DEX Execution Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     DEX Swap Execution Flow                      │
│                                                                  │
│  swap_tokens(from_token, to_token, amount, chain)               │
│       │                                                          │
│       ├──▶ Paper Mode? ──▶ Paper Engine ──▶ Return result       │
│       │                                                          │
│       ▼                                                          │
│  Policy Validation (chain, tokens, amounts)                     │
│       │                                                          │
│       ├──▶ Approval Required? ──▶ Create Proposal ──▶ Wait      │
│       │                                                          │
│       ▼                                                          │
│  DexHandler.build_swap_tx() ──▶ 1inch API                       │
│       │                                                          │
│       ▼                                                          │
│  Signer.sign_transaction() ──▶ Sign with configured signer      │
│       │                                                          │
│       ▼                                                          │
│  send_raw_transaction() ──▶ Broadcast to RPC                    │
│       │                                                          │
│       ▼                                                          │
│  Audit Log ──▶ Return tx_hash                                   │
└─────────────────────────────────────────────────────────────────┘
```

### 5. Market Data Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   Market Data Bus Architecture                   │
│                                                                  │
│  ┌─────────────────┐   Priority 0 (Highest)                     │
│  │ WebSocket Store │◀── exchange_ws (real-time from WS)         │
│  └────────┬────────┘                                            │
│           │                                                      │
│  ┌────────▼────────┐   Priority 1                               │
│  │  Ingest Store   │◀── User-supplied feeds / other MCPs        │
│  └────────┬────────┘                                            │
│           │                                                      │
│  ┌────────▼────────┐   Priority 2 (Fallback)                    │
│  │  CCXT REST      │◀── ccxt_rest (REST API polling)            │
│  └────────┬────────┘                                            │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────┐                                            │
│  │ MarketDataBus   │── Freshness Scoring + Outlier Detection    │
│  │                 │── MARKETDATA_FAIL_CLOSED mode              │
│  └─────────────────┘                                            │
└─────────────────────────────────────────────────────────────────┘
```

### 6. Signing Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Signer Abstraction Layer                     │
│                                                                  │
│  SIGNER_TYPE=env_private_key                                    │
│  ┌─────────────────┐                                            │
│  │ EnvPrivateKey   │── Uses PRIVATE_KEY env var                 │
│  │ Signer          │── Simple, for development/testing          │
│  └─────────────────┘                                            │
│                                                                  │
│  SIGNER_TYPE=keystore                                           │
│  ┌─────────────────┐                                            │
│  │ Keystore        │── Uses KEYSTORE_PATH + KEYSTORE_PASSWORD   │
│  │ Signer          │── Encrypted key file                       │
│  └─────────────────┘                                            │
│                                                                  │
│  SIGNER_TYPE=remote                                             │
│  ┌─────────────────┐                                            │
│  │ Remote          │── Uses SIGNER_REMOTE_URL                   │
│  │ Signer          │── HTTP signer sidecar                      │
│  └─────────────────┘                                            │
│                                                                  │
│  SIGNER_TYPE=cb_mpc_2pc                                         │
│  ┌─────────────────┐                                            │
│  │ Coinbase MPC    │── Uses MPC_SIGNER_URL                      │
│  │ 2PC Signer      │── Institutional-grade custody              │
│  └─────────────────┘                                            │
│                                                                  │
│  Optional: PolicySigner Wrapper                                  │
│  ┌─────────────────┐                                            │
│  │ Validates:      │── Chain IDs, To addresses                  │
│  │                 │── Value limits, Gas limits                 │
│  │                 │── Data size, Contract creation             │
│  └─────────────────┘                                            │
└─────────────────────────────────────────────────────────────────┘
```

### 7. Observability Stack

```
┌─────────────────────────────────────────────────────────────────┐
│                     Observability Components                     │
│                                                                  │
│  ┌─────────────┐                                                │
│  │ Audit Log   │── SQLite with tamper-evident hash chain        │
│  │             │── Tax report export (CSV)                      │
│  └─────────────┘                                                │
│                                                                  │
│  ┌─────────────┐                                                │
│  │ Metrics     │── In-memory counters, timers, gauges           │
│  │             │── Prometheus exposition format                 │
│  └─────────────┘                                                │
│                                                                  │
│  ┌─────────────┐                                                │
│  │ Tracing     │── OpenTelemetry integration (optional)         │
│  │             │── OTLP exporter support                        │
│  └─────────────┘                                                │
│                                                                  │
│  ┌─────────────┐                                                │
│  │ Webhooks    │── Discord notifications                        │
│  │             │── Approval required alerts                     │
│  └─────────────┘                                                │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow: Complete Trade Lifecycle

```
┌─────────────────────────────────────────────────────────────────┐
│              Complete Trade Lifecycle (approve_each mode)        │
│                                                                  │
│  1. Agent: "Buy 0.01 BTC at market"                             │
│       │                                                          │
│       ▼                                                          │
│  2. MCP Server: place_cex_order(BTC/USDT, buy, 0.01)           │
│       │                                                          │
│       ▼                                                          │
│  3. Rate Limiter: Check API rate                                │
│       │                                                          │
│       ▼                                                          │
│  4. Risk Guardian: validate_trade_risk()                        │
│       │  - Position size OK (< 5%)                              │
│       │  - Daily loss OK (< 5%)                                 │
│       │  - Sentiment OK (not falling knife)                     │
│       │                                                          │
│       ▼                                                          │
│  5. Policy Engine: validate_cex_order()                         │
│       │  - Exchange allowed                                      │
│       │  - Symbol allowed                                        │
│       │  - Amount within limits                                  │
│       │                                                          │
│       ▼                                                          │
│  6. Execution Store: Create proposal                            │
│       │  - Generate request_id                                   │
│       │  - Generate confirm_token (single-use)                   │
│       │  - Set TTL (120s)                                        │
│       │                                                          │
│       ▼                                                          │
│  7. Webhook: Notify operator (Discord)                          │
│       │                                                          │
│       ▼                                                          │
│  8. Return to Agent: { approval_required: true, request_id }    │
│       │                                                          │
│       ▼                                                          │
│  9. Operator: Reviews in Web UI, clicks "Approve"               │
│       │                                                          │
│       ▼                                                          │
│  10. API Server: POST /api/approve-trade                        │
│       │   - Verify confirm_token                                 │
│       │   - Check not expired                                    │
│       │   - Execute order                                        │
│       │                                                          │
│       ▼                                                          │
│  11. CexExecutor: Place order via CCXT                          │
│       │                                                          │
│       ▼                                                          │
│  12. Audit Log: Record execution                                │
│       │                                                          │
│       ▼                                                          │
│  13. Return: { ok: true, order: {...} }                         │
└─────────────────────────────────────────────────────────────────┘
```

## Deployment Architectures

### Single-Process (Default)

```
┌─────────────────────────────────────────┐
│              Single Container            │
│  ┌─────────────────────────────────┐   │
│  │      ReadyTrader-Crypto         │   │
│  │  ┌───────────┐ ┌───────────┐   │   │
│  │  │ MCP Server│ │ API Server│   │   │
│  │  └───────────┘ └───────────┘   │   │
│  │  ┌───────────────────────────┐ │   │
│  │  │    SQLite (data/*.db)     │ │   │
│  │  └───────────────────────────┘ │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

### Horizontally Scaled (with Redis/PostgreSQL)

```
┌─────────────────────────────────────────────────────────────────┐
│                    Kubernetes Deployment                         │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  MCP Pod 1   │  │  MCP Pod 2   │  │  MCP Pod 3   │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                 │                    │
│         └─────────────────┴────────┬────────┘                    │
│                                    │                             │
│  ┌─────────────────────────────────▼─────────────────────────┐  │
│  │                   Shared Services                          │  │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐             │  │
│  │  │   Redis   │  │ PostgreSQL│  │  Remote   │             │  │
│  │  │  (Store)  │  │  (Audit)  │  │  Signer   │             │  │
│  │  └───────────┘  └───────────┘  └───────────┘             │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Security Model

### Trust Boundaries

```
┌─────────────────────────────────────────────────────────────────┐
│                        Trust Model                               │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ UNTRUSTED: AI Agent                                      │   │
│  │  - Can request any action                                │   │
│  │  - All requests validated by server                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                       │
│                          ▼                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ TRUSTED: ReadyTrader-Crypto Server                       │   │
│  │  - Owns API keys and signing authority                   │   │
│  │  - Enforces all safety policies                          │   │
│  │  - Controls execution rate and approval                  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                       │
│                          ▼                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ SEMI-TRUSTED: External Services                          │   │
│  │  - Exchanges (assume secure, but verify responses)       │   │
│  │  - Blockchains (trustless verification possible)         │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Defense in Depth

| Layer | Protection         | Implementation                            |
| ----- | ------------------ | ----------------------------------------- |
| 1     | Rate Limiting      | Fixed window limiter per key              |
| 2     | Risk Validation    | Position size, loss limits, sentiment     |
| 3     | Policy Enforcement | Allowlists for chains, tokens, exchanges  |
| 4     | Approval Gate      | Two-step execution with single-use tokens |
| 5     | Signer Policy      | Transaction parameter limits              |
| 6     | Audit Trail        | Tamper-evident log with hash chain        |

## API Server Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Server Structure                      │
│                                                                  │
│  Middleware Stack:                                               │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 1. CORS Middleware                                       │   │
│  │ 2. Rate Limit Middleware                                 │   │
│  │ 3. Authentication (JWT, optional)                        │   │
│  │ 4. Request Tracing (OpenTelemetry, optional)            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  Endpoints:                                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Public:                                                  │   │
│  │   GET  /api/health                                       │   │
│  │                                                          │   │
│  │ Authenticated:                                           │   │
│  │   POST /api/auth/login                                   │   │
│  │   GET  /api/auth/me                                      │   │
│  │   GET  /api/portfolio                                    │   │
│  │   GET  /api/pending-approvals                            │   │
│  │   POST /api/approve-trade                                │   │
│  │   GET  /api/metrics                                      │   │
│  │   GET  /api/strategies                                   │   │
│  │   GET  /api/insights                                     │   │
│  │   GET  /api/trades/history                               │   │
│  │                                                          │   │
│  │ Admin:                                                   │   │
│  │   GET  /api/audit/export                                 │   │
│  │                                                          │   │
│  │ WebSocket:                                               │   │
│  │   WS   /ws (real-time ticker updates)                    │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Configuration Reference

See `env.example` for full configuration reference. Key environment variables:

| Category | Variable                  | Default           | Description                     |
| -------- | ------------------------- | ----------------- | ------------------------------- |
| Mode     | `PAPER_MODE`              | `true`            | Paper vs live trading           |
| Safety   | `LIVE_TRADING_ENABLED`    | `false`           | Enable live execution           |
| Safety   | `TRADING_HALTED`          | `false`           | Emergency kill switch           |
| Safety   | `EXECUTION_APPROVAL_MODE` | `auto`            | `auto` or `approve_each`        |
| Signing  | `SIGNER_TYPE`             | `env_private_key` | Signer backend                  |
| Store    | `STORE_BACKEND`           | `memory`          | `memory`, `redis`, `postgresql` |
| Tracing  | `OTEL_ENABLED`            | `false`           | Enable OpenTelemetry            |
