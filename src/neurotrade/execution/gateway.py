"""Order Execution Layer - CTP/XTP protocol adapters"""
from __future__ import annotations
import asyncio
import logging
import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


logger = logging.getLogger("execution")


class OrderStatus(Enum):
    PENDING = "pending"; SUBMITTED = "submitted"; PARTIAL = "partial"
    FILLED = "filled"; CANCELLED = "cancelled"; REJECTED = "rejected"; ERROR = "error"


class Direction(Enum):
    BUY = "BUY"; SELL = "SELL"


class OrderType(Enum):
    LIMIT = "LIMIT"; MARKET = "MARKET"


@dataclass
class OrderRequest:
    symbol: str; exchange: str; direction: Direction; order_type: OrderType
    quantity: int; price: Optional[float] = None
    order_id: str = field(default_factory=lambda: f"ORD-{uuid.uuid4().hex[:12].upper()}")


@dataclass
class OrderResponse:
    order_id: str; status: OrderStatus = OrderStatus.PENDING
    broker_order_id: str = ""; filled_quantity: int = 0; avg_fill_price: float = 0.0; message: str = ""


class PaperTradingGateway:
    def __init__(self, config=None):
        self._connected = False; self._logged_in = False
        self._orders = {}; self._positions = {}
        self._balance = 10_000_000; self._available = self._balance
        self.logger = logging.getLogger("execution.paper")

    async def connect(self):
        self._connected = True
        self.logger.info(f"Paper trading connected (balance: {self._balance:,.2f})")
        return True

    async def login(self, user_id, password, auth_code, app_id):
        self._logged_in = True
        self.logger.info(f"Paper login: {user_id}")
        return True

    async def logout(self): self._logged_in = False

    async def send_order(self, order: OrderRequest) -> OrderResponse:
        fill_price = order.price * random.uniform(0.999, 1.001) if order.price else 10.0
        turnover = fill_price * order.quantity
        if order.direction == Direction.BUY and turnover > self._available:
            return OrderResponse(order_id=order.order_id, status=OrderStatus.REJECTED, message="Insufficient funds")
        if order.direction == Direction.SELL:
            pk = f"{order.exchange}:{order.symbol}"
            if self._positions.get(pk, {}).get("quantity", 0) < order.quantity:
                return OrderResponse(order_id=order.order_id, status=OrderStatus.REJECTED, message="Insufficient shares")
        if order.direction == Direction.BUY:
            self._available -= turnover
        else:
            self._available += turnover
        pk = f"{order.exchange}:{order.symbol}"
        pos = self._positions.get(pk, {"quantity": 0, "avg_cost": 0})
        if order.direction == Direction.BUY:
            total = pos["quantity"] * pos["avg_cost"] + order.quantity * fill_price
            pos["quantity"] += order.quantity
            pos["avg_cost"] = total / pos["quantity"] if pos["quantity"] > 0 else 0
        else:
            pos["quantity"] -= order.quantity
            if pos["quantity"] == 0:
                pos["avg_cost"] = 0
        self._positions[pk] = pos
        response = OrderResponse(
            order_id=order.order_id, broker_order_id=f"PAPER-{order.order_id}",
            status=OrderStatus.FILLED, filled_quantity=order.quantity,
            avg_fill_price=round(fill_price, 2), message="Paper filled")
        self._orders[order.order_id] = response
        self.logger.info(f"Paper filled: {order.direction.value} {order.quantity} {order.symbol} @ {fill_price:.2f}")
        return response

    async def cancel_order(self, order_id) -> OrderResponse:
        return OrderResponse(order_id=order_id, status=OrderStatus.CANCELLED, message="Cancelled")
    async def query_order(self, order_id) -> OrderResponse:
        return self._orders.get(order_id, OrderResponse(order_id=order_id, status=OrderStatus.ERROR, message="Not found"))
    async def query_positions(self) -> list:
        return [{"symbol": k.split(":")[1], "exchange": k.split(":")[0], **v} for k, v in self._positions.items() if v["quantity"] > 0]
    async def query_account(self) -> dict:
        mv = sum(p["quantity"] * p["avg_cost"] for p in self._positions.values())
        return {"account_id": "PAPER", "balance": self._balance, "available": self._available, "market_value": mv, "total_asset": self._available + mv}


def create_gateway(mode="paper", front_url="", config=None):
    return PaperTradingGateway(config)
