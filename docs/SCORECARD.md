# ReadyTrader-Crypto — Production Scorecard (Target: 10/10)

This scorecard turns “10/10 production quality” into **measurable, repeatable gates**.

## Environment assumptions

- **Python**: 3.12+ (CI uses 3.12; `pyproject.toml` requires `>=3.12`)
- **Primary run mode**: Docker-first, with optional local dev

## Quality gates (must be green)

### Lint (ruff)

```bash
ruff check .
```

- **Pass**: exit code 0
- **Notes**: import sorting and unused imports must be fixed repo-wide.

### Unit tests (pytest)

```bash
pytest -q
```

- **Pass**: exit code 0
- **Policy**: no stub tests (`pass`) in the suite once we reach 10/10.

### Static security scan (bandit)

```bash
bandit -q -r . -c bandit.yaml
```

- **Pass**: exit code 0 (or only explicitly-configured skips)

### Dependency vulnerability audit (pip-audit)

```bash
pip-audit -r requirements.txt
```

- **Pass**: no known vulns in runtime deps.

### Tool-surface correctness (docs drift)

The documented tool catalog must be generated from the **actual registered tools**.

```bash
python tools/generate_tool_docs.py
git diff --exit-code docs/TOOLS.md
```

- **Pass**: `docs/TOOLS.md` matches the running MCP tool registry.

### “No stubs/TODOs” runtime policy

```bash
pytest -q tests/test_no_stubs_policy.py
```

- **Pass**: no `TODO/FIXME/XXX` markers and no “simulated live” runtime paths.

## Baseline snapshot (captured 2026-01-01)

### What is currently green

- **Tests**: `pytest -q` passes.
- **Bandit**: `bandit -q -r . -c bandit.yaml` passes (warnings are informational).

### What is currently red (must be fixed to reach 10/10)

- **Lint**: `ruff check .` fails on:
  - import ordering in `api_server.py` and `app/tools/execution.py`
  - unused imports in `signing/cb_mpc_2pc.py`
- **Dependency audit**: `pip-audit -r requirements.txt` reports vulnerabilities in `starlette==0.41.3`.

### Tool-surface drift (must be eliminated)

- `docs/TOOLS.md` and `tools/generate_tool_docs.py` currently reference a non-existent `server.py`.
- The docs list tools (e.g., ops/marketdata ingestion/approval helpers) that are not currently implemented/registered under `app/tools/*` + `app/main.py`.
