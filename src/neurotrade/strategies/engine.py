"""Trading Strategies"""
from __future__ import annotations
import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict


@dataclass
class Signal:
    symbol: str; exchange: str; direction: str; confidence: float; price: float
    quantity: int; reason: str; strategy: str
    timestamp: datetime = field(default_factory=datetime.now); metadata: dict = field(default_factory=dict)


@dataclass
class StrategyConfig:
    name: str; enabled: bool = True; symbols: list = None; exchanges: list = None
    max_position_pct: float = 0.10; min_confidence: float = 0.60

    def __post_init__(self):
        if self.symbols is None: self.symbols = []
        if self.exchanges is None: self.exchanges = []


class Strategy(ABC):
    def __init__(self, config: StrategyConfig):
        self.config = config
        self.logger = logging.getLogger(f"strategy.{config.name}")

    @abstractmethod
    async def analyze(self, symbol: str, exchange: str, tick_data: dict) -> Optional[Signal]: ...

    async def on_tick(self, symbol, exchange, tick_data) -> Optional[Signal]:
        if not self.config.enabled or symbol not in self.config.symbols:
            return None
        return await self.analyze(symbol, exchange, tick_data)


class MeanReversionStrategy(Strategy):
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.price_history: Dict[str, list] = {}
        self.rebalance_threshold = 0.02

    async def analyze(self, symbol: str, exchange: str, tick_data: dict) -> Optional[Signal]:
        price = tick_data.get("last_price")
        if not price: return None
        key = f"{exchange}:{symbol}"
        if key not in self.price_history: self.price_history[key] = []
        self.price_history[key].append(price)
        if len(self.price_history[key]) > 20:
            self.price_history[key] = self.price_history[key][-20:]
        prices = self.price_history[key]
        if len(prices) < 5: return None
        ma20 = sum(prices) / len(prices)
        deviation = (price - ma20) / ma20
        if deviation < -self.rebalance_threshold:
            conf = min(abs(deviation) * 10, 1.0)
            if conf >= self.config.min_confidence:
                return Signal(symbol=symbol, exchange=exchange, direction="BUY", confidence=conf, price=price, quantity=100, reason=f"Mean reversion: {deviation:.2%} below MA20", strategy=self.config.name)
        elif deviation > self.rebalance_threshold:
            conf = min(deviation * 10, 1.0)
            if conf >= self.config.min_confidence:
                return Signal(symbol=symbol, exchange=exchange, direction="SELL", confidence=conf, price=price, quantity=100, reason=f"Mean reversion: {deviation:.2%} above MA20", strategy=self.config.name)
        return None


class StrategyManager:
    def __init__(self):
        self.strategies: List[Strategy] = []
        self.logger = logging.getLogger("strategies.manager")

    def add_strategy(self, strategy: Strategy):
        self.strategies.append(strategy)

    async def evaluate_all(self, symbol, exchange, tick_data) -> List[Signal]:
        signals = []
        for strategy in self.strategies:
            try:
                sig = await strategy.on_tick(symbol, exchange, tick_data)
                if sig: signals.append(sig)
            except Exception as e:
                self.logger.error(f"Strategy {strategy.config.name} error: {e}")
        return signals
