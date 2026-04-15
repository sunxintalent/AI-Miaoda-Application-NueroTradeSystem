"""Risk Manager - Multi-layer risk controls"""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from datetime import datetime, time as dtime
from enum import Enum
from typing import Dict, Optional


class RiskLevel(Enum):
    PASS = "pass"; WARN = "warn"; REJECT = "reject"; HALT = "halt"


@dataclass
class RiskCheckResult:
    level: RiskLevel
    message: str
    details: dict = field(default_factory=dict)


@dataclass
class Order:
    symbol: str; exchange: str; direction: str; order_type: str; quantity: int
    price: Optional[float] = None; order_id: str = ""; timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Position:
    symbol: str; exchange: str; quantity: int = 0; avg_cost: float = 0.0
    market_value: float = 0.0; unrealized_pnl: float = 0.0; realized_pnl: float = 0.0


@dataclass
class RiskConfig:
    max_single_position_pct: float = 0.10
    max_total_position_pct: float = 0.80
    max_order_value: float = 1_000_000
    max_single_order_quantity: int = 1_000_000
    max_daily_loss_pct: float = 0.02
    circuit_breaker_index_drop_pct: float = 0.05
    approval_required_pct: float = 0.15


class RiskManager:
    def __init__(self, config: RiskConfig = None):
        self.config = config or RiskConfig()
        self.positions: Dict[str, Position] = {}
        self.daily_pnl: float = 0.0
        self.daily_trades: int = 0
        self.halted: bool = False
        self.halt_reason: str = ""
        self.logger = logging.getLogger("risk.manager")

    def _is_trading_hours(self) -> bool:
        now = datetime.now().time()
        return (dtime(9, 15) <= now <= dtime(11, 30)) or (dtime(12, 30) <= now <= dtime(15, 15))

    async def pre_trade_check(self, order: Order, portfolio_value: float) -> RiskCheckResult:
        if self.halted:
            return RiskCheckResult(RiskLevel.REJECT, "System halted", {"halt_reason": self.halt_reason})
        if not self._is_trading_hours():
            return RiskCheckResult(RiskLevel.REJECT, "Outside trading hours")
        if order.quantity <= 0:
            return RiskCheckResult(RiskLevel.REJECT, "Invalid quantity")
        order_value = order.quantity * (order.price or 0)
        if order_value > self.config.max_order_value:
            return RiskCheckResult(RiskLevel.REJECT, f"Order value exceeds limit: {order_value:,.0f}")
        if order.quantity > self.config.max_single_order_quantity:
            return RiskCheckResult(RiskLevel.REJECT, "Quantity exceeds limit")
        pos_key = f"{order.exchange}:{order.symbol}"
        current_pos = self.positions.get(pos_key)
        current_qty = current_pos.quantity if current_pos else 0
        new_qty = (current_qty + order.quantity) if order.direction == "BUY" else (current_qty - order.quantity)
        new_pos_value = new_qty * (order.price or (current_pos.avg_cost if current_pos else 0))
        position_pct = new_pos_value / portfolio_value if portfolio_value > 0 else 0
        if position_pct > self.config.max_single_position_pct:
            return RiskCheckResult(RiskLevel.REJECT, f"Position limit exceeded: {position_pct:.1%}")
        if self.daily_pnl < -portfolio_value * self.config.max_daily_loss_pct:
            return RiskCheckResult(RiskLevel.HALT, f"Daily loss limit exceeded: {self.daily_pnl:,.0f}")
        return RiskCheckResult(RiskLevel.PASS, "Risk check passed")

    def update_position(self, order: Order, executed_price: float) -> Position:
        pos_key = f"{order.exchange}:{order.symbol}"
        pos = self.positions.get(pos_key) or Position(symbol=order.symbol, exchange=order.exchange)
        if order.direction == "BUY":
            total_cost = pos.quantity * pos.avg_cost + order.quantity * executed_price
            pos.quantity += order.quantity
            pos.avg_cost = total_cost / pos.quantity if pos.quantity > 0 else 0
        else:
            pos.realized_pnl += (executed_price - pos.avg_cost) * min(order.quantity, pos.quantity)
            pos.quantity -= order.quantity
            if pos.quantity == 0:
                pos.avg_cost = 0
        self.positions[pos_key] = pos
        self.daily_trades += 1
        return pos

    def trigger_circuit_breaker(self, reason: str) -> None:
        self.halted = True
        self.halt_reason = reason
        self.logger.critical(f"CIRCUIT BREAKER: {reason}")

    def get_portfolio_summary(self) -> dict:
        return {
            "halted": self.halted, "halt_reason": self.halt_reason,
            "daily_pnl": self.daily_pnl, "daily_trades": self.daily_trades,
            "positions": {k: {"qty": p.quantity, "avg_cost": p.avg_cost} for k, p in self.positions.items()},
        }
