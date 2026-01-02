"""
Backwards-compatible entrypoint.

`server.py` is the canonical FastMCP entrypoint and tool registry.
This module re-exports `mcp` for imports like `from app.main import mcp`.
"""

from __future__ import annotations

from server import main, mcp

__all__ = ["main", "mcp"]

if __name__ == "__main__":
    main()
