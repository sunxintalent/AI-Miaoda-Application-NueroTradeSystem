"""Market Data Feed - SSE/SZSE Level-2"""
from __future__ import annotations
import asyncio
import logging
import random
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Optional

logger = logging.getLogger("data")


class Exchange(Enum):
    SSE = "SSE"; SZSE = "SZSE"


@dataclass
class Tick:
    symbol: str; exchange: str; timestamp: datetime
    last_price: float; open_price: float; high_price: float; low_price: float
    volume: int; turnover: float
    bid_price1: float; bid_volume1: int; ask_price1: float; ask_volume1: int
    bid_price2: float = 0; bid_volume2: int = 0; bid_price3: float = 0; bid_volume3: int = 0
    ask_price2: float = 0; ask_volume2: int = 0; ask_price3: float = 0; ask_volume3: int = 0
    pre_close: float = 0; change: float = 0; change_pct: float = 0


class MarketDataProvider:
    def __init__(self):
        self._ticks: Dict[str, Tick] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def connect(self):
        self._running = True
        self._task = asyncio.create_task(self._generate_ticks())
        logger.info("Market data connected (mock)")

    async def _generate_ticks(self):
        base_prices = {"SSE:600519": 1850.0, "SSE:600036": 38.5, "SZSE:000858": 28.5, "SZSE:000001": 12.3}
        while self._running:
            for key, base_price in list(base_prices.items()):
                exchange, symbol = key.split(":", 1)
                cp = random.uniform(-0.02, 0.02)
                price = base_price * (1 + cp)
                self._ticks[key] = Tick(
                    symbol=symbol, exchange=exchange, timestamp=datetime.now(),
                    last_price=round(price, 2),
                    open_price=round(base_price * random.uniform(0.98, 1.02), 2),
                    high_price=round(price * 1.01, 2),
                    low_price=round(price * 0.99, 2),
                    volume=random.randint(10000, 1000000),
                    turnover=random.uniform(1e6, 1e8),
                    bid_price1=round(price * 0.9998, 2), bid_volume1=random.randint(100, 10000),
                    ask_price1=round(price * 1.0002, 2), ask_volume1=random.randint(100, 10000),
                    pre_close=base_price, change=round(price - base_price, 2), change_pct=round(cp * 100, 2))
                base_prices[key] = price
            await asyncio.sleep(1)

    async def subscribe(self, symbols, exchange="SSE"): pass
    async def unsubscribe(self, symbols, exchange="SSE"): pass
    async def get_tick(self, symbol, exchange="SSE"): return self._ticks.get(f"{exchange}:{symbol}")
    async def close(self): self._running = False; logger.info("Market data disconnected")


def create_market_data_provider(provider_type, config):
    return MarketDataProvider()
