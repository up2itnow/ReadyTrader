from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from exchange_provider import ExchangeProvider

from .store import InMemoryMarketDataStore, TickerSnapshot


class MarketDataProvider:
    provider_id: str

    def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        raise NotImplementedError

    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int) -> List[Any]:
        raise NotImplementedError


@dataclass(frozen=True)
class IngestMarketDataProvider(MarketDataProvider):
    store: InMemoryMarketDataStore
    provider_id: str = "ingest"

    def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        snap: Optional[TickerSnapshot] = self.store.get_ticker(symbol=symbol)
        if not snap:
            raise ValueError("No ingested ticker available")
        return {
            "last": snap.last,
            "bid": snap.bid,
            "ask": snap.ask,
            "timestamp": snap.timestamp_ms,
            "source": snap.source,
        }

    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int) -> List[Any]:
        data = self.store.get_ohlcv(symbol=symbol, timeframe=timeframe, limit=limit)
        if data is None:
            raise ValueError("No ingested OHLCV available")
        return data


@dataclass(frozen=True)
class CcxtMarketDataProvider(MarketDataProvider):
    exchange_provider: ExchangeProvider
    provider_id: str = "ccxt_rest"

    def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        return self.exchange_provider.fetch_ticker(symbol)

    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int) -> List[Any]:
        return self.exchange_provider.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)

