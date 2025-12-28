from __future__ import annotations

import json
import os
import time
import uuid
from typing import Any, Dict, Optional


def build_log_context(*, tool: str) -> Dict[str, Any]:
    """
    Build a per-invocation context object for structured logs.

    We keep this intentionally minimal to avoid leaking sensitive data.
    """
    return {
        "tool": tool,
        "request_id": str(uuid.uuid4()),
        "ts_ms": int(time.time() * 1000),
        "service": os.getenv("READYTRADER_SERVICE_NAME", "readytrader"),
    }


def log_event(event: str, *, ctx: Dict[str, Any], data: Optional[Dict[str, Any]] = None) -> None:
    """
    Emit a single-line JSON log event to stdout.
    """
    payload = dict(ctx)
    payload["event"] = event
    if data:
        payload["data"] = data
    print(json.dumps(payload, sort_keys=True))

