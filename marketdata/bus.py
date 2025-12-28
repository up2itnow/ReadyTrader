from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from .providers import MarketDataProvider


@dataclass(frozen=True)
class MarketDataResult:
    source: str
    data: Any


class MarketDataBus:
    """
    Simple priority-ordered market data router.

    Provider order matters. A typical ordering is:
    1) Ingested data (user-supplied feed / other MCP)
    2) CCXT REST fallback
    """

    def __init__(self, providers: List[MarketDataProvider]) -> None:
        self._providers = list(providers)

    def fetch_ticker(self, symbol: str) -> MarketDataResult:
        last_err: Exception | None = None
        for p in self._providers:
            try:
                return MarketDataResult(source=p.provider_id, data=p.fetch_ticker(symbol))
            except Exception as e:
                last_err = e
                continue
        raise ValueError(f"All providers failed to fetch ticker for {symbol}. Last error: {last_err}")

    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int) -> MarketDataResult:
        last_err: Exception | None = None
        for p in self._providers:
            try:
                return MarketDataResult(
                    source=p.provider_id,
                    data=p.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit),
                )
            except Exception as e:
                last_err = e
                continue
        raise ValueError(f"All providers failed to fetch OHLCV for {symbol}. Last error: {last_err}")

    def status(self) -> Dict[str, Any]:
        return {"providers": [p.provider_id for p in self._providers]}

