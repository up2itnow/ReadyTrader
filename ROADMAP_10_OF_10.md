## ReadyTrader - Roadmap to 10/10 across Professionalism, Docs, Usability, Marketability, Feature Depth

This roadmap is intentionally ambitious. The goal is to turn ReadyTrader from a high-quality OSS MCP trading server into a **trusted, distribution-grade** product that is safe to operate and easy to adopt.

### Current status
- **Phase 0 is complete** (release readiness docs, tool catalog generation, dev requirements split, CI/Docker alignment).
- Next up: **Phase 1** (reliability + operator confidence).

### Scoring rubric (what 10/10 means)
- **Professionalism**: reproducible builds, clean packaging, strong governance, stable APIs, thoughtful architecture, no foot-guns.
- **Docs**: complete, accurate, and easy to navigate; includes tool catalog, configuration, runbooks, and examples.
- **Usability**: minimal setup, sensible defaults, operator-friendly controls, clear error messages, fast feedback loops.
- **Marketability**: strong differentiation with credible claims; polished messaging; easy to demo.
- **Feature depth**: robust execution lifecycle, broad exchange coverage, high-quality market data, and secure custody patterns.

### How to use this roadmap
- Each phase has **deliverables** + **measurable acceptance criteria**.
- "Done" requires **evidence**: tests, docs, or operator artifacts proving it works.
- Safety rules remain non-negotiable:
  - Live trading is **opt-in** (`LIVE_TRADING_ENABLED=true`) and gated by **per-process consent**.
  - Consent **never persists across restarts** (by design).

### 10/10 definitions of done (by category)
- **Professionalism (10/10)**
  - CI green on `main` (lint/tests/security/audit) with **no flaky tests**.
  - Reproducible installs: pinned runtime deps; pinned dev tooling; deterministic Docker build.
  - Tagged releases + changelog discipline + versioning policy.
  - Clear maintenance posture (issue templates, PR templates, contribution expectations).
- **Docs (10/10)**
  - Accurate README + quickstart + runbook.
  - Generated tool catalog stays in sync with code (`docs/TOOLS.md` generated from `server.py`).
  - Clear config template (`env.example`) and safe defaults guidance.
  - Architecture overview and troubleshooting paths.
- **Usability (10/10)**
  - New user can run a paper-mode demo in **<10 minutes**.
  - Clear errors with stable codes + self-serve operator introspection tools.
  - Presets + progressive disclosure reduce configuration friction.
- **Marketability (10/10)**
  - Aggressive but credible messaging (no overclaims, no "guaranteed profit" framing).
  - High-conversion demo paths (paper/stress/safety demos).
  - Distribution channels covered (Agent Zero community, MCP registries, etc.).
- **Feature depth (10/10)**
  - Exchange breadth + execution depth (order lifecycle, partial fills, replace/cancel flows).
  - Market data quality (ws-first + ingest + rest fallback with scoring/validation).
  - Security/custody posture (strong signer policies, rotation guidance, least-privilege patterns).

### Release ladder (recommended)
This keeps expectations clear and prevents "we have everything" ambiguity.
- **v0.1 (current)**: connector-grade + safety moat + distribution polish (Phase 0 done).
- **v0.2 (alpha)**: long-running reliability + operator confidence (Phase 1).
- **v0.3 (beta)**: execution depth + market data quality (Phases 2-3).
- **v0.4**: operator/observability maturity (Phase 4).
- **v0.5**: security/custody hardening (Phase 5).
- **v1.0**: productization and ecosystem packaging (Phase 6).

---

## Phase 0 - Distribution polish (1-2 days) [COMPLETED]
**Objective**: Make the repo feel ship-ready and reduce adoption friction.

Delivered (already merged):
- Runtime vs dev requirements: `requirements.txt` + `requirements-dev.txt`
- CI installs dev requirements deterministically and audits runtime dependencies
- Config template: `env.example` (copy to `.env`)
- Generated tool catalog: `docs/TOOLS.md` (`tools/generate_tool_docs.py`)
- Docker context tightened (`.dockerignore`) and Python version aligned
- Basic thread-safety for shared in-memory stores used by websocket threads
- Release hygiene docs:
  - `RELEASE_READINESS_CHECKLIST.md`
  - `docs/POSITIONING.md`

Evidence / acceptance criteria:
- Fresh clone -> `docker build` succeeds
- Fresh clone -> `pip install -r requirements-dev.txt` + checks pass
- README points to tool catalog + config template + positioning + readiness checklist

---

## Phase 1 - Reliability & operational confidence (3-7 days)
**Objective**: Make ReadyTrader stable under long-running workloads and multi-tool concurrency.

### Phase 1A - Concurrency hardening & resource boundaries
Deliverables:
- Verify all shared state is thread-safe (stores, rate limiter, proposal store, WS buffers).
- Ensure all WS/public/private streams are bounded in memory and cannot grow unbounded.
- Standardize stream lifecycle:
  - start is idempotent
  - stop is fast (<3s) and reliable
  - reconnection uses exponential backoff + jitter

Implementation ideas:
- Add a small, opt-in soak runner (not CI) in `tools/soak_test.py`.
- Add metrics around WS health: last_message_age_ms, reconnect_count, parse_failures.

Acceptance criteria:
- 1-4 hour soak test with WS streams + repeated tool calls:
  - no crashes
  - bounded memory growth
  - deterministic stop/start behavior

### Phase 1B - Optional persistence without violating consent rules
Deliverables:
- Optional local DB (e.g., SQLite) for:
  - execution audit log (paper + live)
  - idempotency keys for already executed actions
  - optional operator snapshots (debug)
- **Consent remains in-memory only** and never persists across restarts.
- If proposals are persisted, they must be invalidated on restart (boot/session id) so stale approvals cannot execute.

Acceptance criteria:
- With persistence enabled, audit entries survive restarts; consent does not.

### Phase 1C - Operator feedback + stable subsystem errors
Deliverables:
- Expand `get_health()` into a clear breakdown:
  - marketdata providers
  - WS streams + last_error + last_message age
  - private streams
  - signer readiness
  - policy configuration sanity
- Stable error codes across major subsystems (marketdata, execution, signer, policy).
- Add `docs/ERRORS.md` mapping codes -> operator actions.

Acceptance criteria:
- Operator can answer "what's running, what's failing, and why" in <5 minutes.

Risks & mitigations:
- **Hidden concurrency issues**: add targeted tests + locks + bounded buffers.
- **Persistence foot-guns**: do not persist consent; invalidate proposals on restart.

---

## Phase 2 - Exchange breadth & execution depth (1-3 weeks)
**Objective**: Be best-in-class among MCP trading connectors.

### Phase 2A - Exchange capability matrix (truthful, documented)
Deliverables:
- `docs/EXCHANGES.md` listing per exchange:
  - spot/swap/future support
  - order types supported
  - private WS support (if any)
  - credential requirements
  - known caveats
- "Supported" vs "Experimental" labels.

Acceptance criteria:
- A user can quickly decide if an exchange/market_type is suitable.

### Phase 2B - Order lifecycle primitives (consistent internal model)
Deliverables:
- Normalize order statuses across CCXT exchanges.
- First-class partial fills + fill aggregation.
- Replace/modify semantics with best-effort fallback per exchange.
- Treat `execution/models.py` as a strict internal contract.

Acceptance criteria:
- For top exchanges (Binance/Coinbase/Kraken/Bybit/OKX):
  - place -> monitor -> fill/partial -> cancel -> replace flows are reliable.

### Phase 2C - Private WS order updates beyond Binance (where supported)
Deliverables:
- Add additional exchanges for private order updates (where reliable).
- Normalize update events and keep bounded in memory (and optionally audit-log them).

Acceptance criteria:
- At least 2-3 exchanges have reliable private updates without polling.

### Phase 2D - Execution robustness
Deliverables:
- Standard retry/backoff for transient CCXT network errors.
- Strong idempotency story for order placement (avoid duplicates on retries).

Acceptance criteria:
- Under induced transient failures (timeouts/disconnects), tools fail predictably and avoid duplicate placement.

---

## Phase 3 - Market data quality & bring-your-own feeds (1-2 weeks)
**Objective**: High-quality market data routing with user-provided feeds as first-class.

### Phase 3A - Freshness scoring & source selection
Deliverables:
- MarketDataBus chooses sources by:
  - freshness (timestamp age)
  - configured priority (ws > ingest > rest)
  - sanity checks (non-zero, non-negative, monotonic timestamps)
- `get_ticker()` returns selected source + freshness metadata.

Acceptance criteria:
- Operators can run "ws-first + ingest fallback + rest fallback" and see exactly why a source was selected.

### Phase 3B - Normalization layer
Deliverables:
- Consistent symbol normalization across ws/ingest/rest.
- Timestamp normalization to ms with documented assumptions.

Acceptance criteria:
- Same symbol yields the same canonical representation across all sources.

### Phase 3C - External feed plugin interface
Deliverables:
- Provider plugin interface beyond manual `ingest_*` calls.
- Example providers (oracle, custom adapter).

Acceptance criteria:
- A user can add a new feed without patching core modules.

### Phase 3D - Validation & guardrails
Deliverables:
- Outlier detection (spike protection) and stale-data detection.
- Optional execution fail-closed mode if market data is stale/outlier.

Acceptance criteria:
- Bad ticks do not silently flow into execution decisions.

---

## Phase 4 - Production operator layer (1-2 weeks)
**Objective**: Observability that matches real ops expectations.

### Phase 4A - Logging maturity
Deliverables:
- Log levels and redaction rules (never log secrets/keys).
- Request correlation where feasible across multi-step tool flows.

Acceptance criteria:
- Operators can filter by tool/request id and see a complete lifecycle.

### Phase 4B - Metrics maturity
Deliverables:
- Metrics coverage for:
  - ws reconnects, last message age, parse failures
  - execution attempts/errors by tool
- Optional Prometheus export mode (off by default).

Acceptance criteria:
- Minimal alert rules can be written for common failure modes.

### Phase 4C - Operator playbooks
Deliverables:
- Expand `RUNBOOK.md` with incident scenarios:
  - rate limit storms
  - websocket disconnect loops
  - exchange outage / degraded mode
  - signer unreachable
  - policy blocks

Acceptance criteria:
- Operator can answer "what's running, what's failing, and why" in <5 minutes.

---

## Phase 5 - Security & custody (2-4 weeks)
**Objective**: Make key custody and signing policies first-class.

### Phase 5A - Remote signer hardening (policy-first)
Deliverables:
- Explicit signing-intent schema for remote signer requests.
- Spend limits and allowlists enforced at multiple layers:
  - policy engine (request validation)
  - signer policy (refuse disallowed signatures)
- Chain allowlists, to-address allowlists, token allowlists where applicable.

Acceptance criteria:
- Misconfiguration (wrong chain/address/limit) fails closed with a clear error code.

### Phase 5B - Secrets and rotation UX
Deliverables:
- Keystore setup/rotation guides.
- Document least-privilege patterns for CEX keys (trade-only, no withdrawal where possible).

Acceptance criteria:
- New operator can rotate keys without guessing.

### Phase 5C - Security automation
Deliverables:
- Expanded CI security posture (additional SAST checks, secret scanning guidance).
- Threat model doc for live trading deployments.

Acceptance criteria:
- Security posture is explicit and reviewable.

---

## Phase 6 - Productization & ecosystem (ongoing)
**Objective**: Make ReadyTrader easy to find, evaluate, and adopt.

### Phase 6A - Fast demo paths (high conversion, low risk)
Deliverables:
- Paper-mode quick demos and example agent prompts.
- Stress-test demo that produces artifacts and a clear narrative.
- Screenshot/gif assets for GitHub + Discord.

Acceptance criteria:
- A new user can evaluate and run a paper-mode demo in <10 minutes.

### Phase 6B - Distribution channels
Deliverables:
- Smithery (or equivalent) install path and metadata.
- Release notes discipline and "what changed" highlights.

Acceptance criteria:
- One-line install + smoke test instructions exist and work.

### Phase 6C - Docs as a product surface
Deliverables:
- Keep `/docs` tidy with a clear entrypoint and minimal navigation.
- Keep `docs/POSITIONING.md` updated to avoid credibility drift.

Acceptance criteria:
- Docs answer the top operator questions without requiring Discord support.

---

## Recommended execution order (practical)
- Phase 1 (reliability) unlocks confidence for everything else.
- Phase 2 + 3 unlock connector leadership (execution + data).
- Phase 4 + 5 unlock operator/security trust for serious deployments.
- Phase 6 unlocks distribution velocity.
