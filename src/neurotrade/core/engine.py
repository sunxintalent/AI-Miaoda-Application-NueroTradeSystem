"""NeuroTrade Core Engine"""
from __future__ import annotations
import asyncio
import logging
import signal
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

from ..risk.manager import RiskManager, RiskConfig, Order, RiskLevel
from ..execution.gateway import create_gateway, Direction, OrderRequest, OrderType, OrderStatus
from ..data.market_data import create_market_data_provider, MarketDataProvider, Tick
from ..strategies.engine import StrategyManager, StrategyConfig, MeanReversionStrategy, Signal
from ..persistence.db import Database
from ..monitoring.alerts import AlertManager


logger = logging.getLogger("core")


class TradingMode(Enum):
    PAPER = "paper"
    LIVE = "live"


@dataclass
class TradingConfig:
    mode: str = "paper"
    symbols: list = field(default_factory=list)
    exchanges: list = field(default_factory=list)
    broker_front_url: str = ""
    broker_app_id: str = ""
    broker_auth_code: str = ""
    broker_user_id: str = ""
    broker_password: str = ""
    data_provider: str = "mock"
    data_api_key: str = ""
    risk_config: RiskConfig = None
    log_level: str = "INFO"


class NeuroTradeEngine:
    def __init__(self, config: TradingConfig):
        self.config = config
        self.running = False
        self._shutdown_event = asyncio.Event()
        self.risk_manager = RiskManager(config.risk_config)
        self.gateway = None
        self.market_data: Optional[MarketDataProvider] = None
        self.strategy_manager = StrategyManager()
        self.database = Database()
        self.alert_manager = AlertManager()
        self._filled_orders = []
        logging.basicConfig(
            level=getattr(logging, config.log_level),
            format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
        )
        self.logger = logging.getLogger("core.engine")

    async def initialize(self) -> None:
        self.logger.info(f"Initializing NeuroTrade v1.0 in {self.config.mode} mode")
        self.market_data = create_market_data_provider(self.config.data_provider, {})
        await self.market_data.connect()
        for exchange in self.config.exchanges:
            await self.market_data.subscribe(self.config.symbols, exchange)
        self.gateway = create_gateway(self.config.mode, self.config.broker_front_url, {})
        await self.gateway.connect()
        if self.config.mode == "paper":
            await self.gateway.login("paper_user", "paper", "paper", "paper")
        else:
            if not await self.gateway.login(
                self.config.broker_user_id, self.config.broker_password,
                self.config.broker_auth_code, self.config.broker_app_id
            ):
                raise RuntimeError("Broker login failed")
        for symbol in self.config.symbols:
            exchange = "SSE" if symbol.startswith(("6", "5")) else "SZSE"
            self.strategy_manager.add_strategy(MeanReversionStrategy(
                StrategyConfig(name="mean_reversion", symbols=[symbol], exchanges=[exchange])))
        self.logger.info(f"Initialized: {len(self.config.symbols)} symbols")

    async def start(self) -> None:
        if self.running:
            return
        await self.initialize()
        self.running = True
        self.logger.info("NeuroTrade engine started")
        while self.running and not self._shutdown_event.is_set():
            try:
                await self._trading_loop()
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Loop error: {e}")
                await asyncio.sleep(5)

    async def _trading_loop(self) -> None:
        account = await self.gateway.query_account()
        portfolio_value = account.get("total_asset", 0)
        for symbol in self.config.symbols:
            exchange = "SSE" if symbol.startswith(("6", "5")) else "SZSE"
            tick = await self.market_data.get_tick(symbol, exchange)
            if not tick:
                continue
            tick_dict = {
                "last_price": tick.last_price, "open_price": tick.open_price,
                "high_price": tick.high_price, "low_price": tick.low_price,
                "volume": tick.volume, "change_pct": tick.change_pct,
                "bid_price1": tick.bid_price1, "ask_price1": tick.ask_price1,
            }
            signals = await self.strategy_manager.evaluate_all(symbol, exchange, tick_dict)
            for sig in signals:
                await self._process_signal(sig, portfolio_value)

    async def _process_signal(self, sig: Signal, portfolio_value: float) -> None:
        self.logger.info(f"Signal: {sig.direction} {sig.symbol} @ {sig.price} ({sig.confidence:.0%})")
        order = Order(
            symbol=sig.symbol, exchange=sig.exchange, direction=sig.direction,
            order_type="LIMIT", quantity=sig.quantity, price=sig.price,
        )
        risk_result = await self.risk_manager.pre_trade_check(order, portfolio_value)
        if risk_result.level == RiskLevel.REJECT:
            self.logger.warning(f"REJECTED: {risk_result.message}")
            return
        if risk_result.level == RiskLevel.HALT:
            self.logger.critical(f"HALTED: {risk_result.message}")
            return
        dir_enum = Direction.BUY if sig.direction == "BUY" else Direction.SELL
        response = await self.gateway.send_order(
            OrderRequest(symbol=order.symbol, exchange=order.exchange,
                direction=dir_enum, order_type=OrderType.LIMIT,
                quantity=order.quantity, price=order.price))
        if response.status == OrderStatus.FILLED:
            self.logger.info(f"FILLED: {sig.direction} {sig.quantity} {sig.symbol} @ {response.avg_fill_price}")
            self.risk_manager.update_position(order, response.avg_fill_price)
            self._filled_orders.append(response)

    async def stop(self) -> None:
        if not self.running:
            return
        self.logger.info("Stopping engine...")
        self.running = False
        if self.market_data:
            await self.market_data.close()
        if self.gateway:
            await self.gateway.logout()
        self.logger.info("Engine stopped")

    def get_status(self) -> dict:
        return {
            "running": self.running, "mode": self.config.mode,
            "symbols": self.config.symbols,
            "filled_orders": len(self._filled_orders),
        }


async def run_doctor() -> dict:
    import sys as _sys
    import importlib as _il
    checks = [
        ("Python >=3.10", _sys.version_info >= (3, 10), f"{_sys.version_info.major}.{_sys.version_info.minor}"),
    ]
    for mod in ["asyncio", "logging", "dataclasses", "enum"]:
        try:
            _il.import_module(mod)
            checks.append((f"stdlib.{mod}", True, "OK"))
        except ImportError:
            checks.append((f"stdlib.{mod}", False, "MISSING"))
    for mod in ["aiohttp"]:
        try:
            _il.import_module(mod)
            checks.append((f"Package.{mod}", True, "OK"))
        except ImportError:
            checks.append((f"Package.{mod}", False, "pip install aiohttp"))
    return {"checks": checks, "total": len(checks), "passed": sum(1 for _, ok, _ in checks if ok)}
