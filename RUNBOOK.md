## ReadyTrader Runbook (Docker-first)

### Common operations

#### Verify health
- Use MCP tool: `get_health()` (Phase 4)\n
- If health fails:\n
  - confirm environment variables\n
  - confirm exchange endpoints reachable\n
  - confirm rate limits and policy allowlists\n

#### Kill switch (live trading)
- Set `TRADING_HALTED=true` and restart the container.\n

#### Rotate secrets
- Prefer keystore or remote signer in live environments.\n
- Rotate `CEX_*` credentials by updating env vars and restarting.\n

#### Debug execution failures
- Look for JSON logs with `event=tool_error`.\n
- Use `list_pending_executions()` for approve-each mode.\n
- Re-run failed operations with an `idempotency_key` to avoid duplicates.\n

### Backup/restore (paper mode)
- Paper ledger is stored in `paper.db` (ignored by git).\n
- Back up by copying the file while the container is stopped.\n

