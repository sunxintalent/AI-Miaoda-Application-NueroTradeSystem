"""SQLite persistence"""
from __future__ import annotations
import json
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


class Database:
    def __init__(self, db_path: str = "/tmp/neurotrade.db"):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _init_db(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY, order_id TEXT UNIQUE, symbol TEXT, exchange TEXT, direction TEXT, order_type TEXT, quantity INTEGER, price REAL, status TEXT, broker_order_id TEXT, filled_quantity INTEGER DEFAULT 0, avg_fill_price REAL DEFAULT 0, message TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS audit_log (id INTEGER PRIMARY KEY, event_type TEXT, entity_id TEXT, details TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
            CREATE INDEX IF NOT EXISTS idx_orders_created ON orders(created_at);
            CREATE INDEX IF NOT EXISTS idx_orders_symbol ON orders(symbol);
        """)
        self._conn.commit()
        logging.getLogger("persistence").info(f"Database: {self.db_path}")

    def log_order(self, order, response):
        try:
            self._conn.execute("INSERT OR REPLACE INTO orders (order_id, symbol, exchange, direction, order_type, quantity, price, status, broker_order_id, filled_quantity, avg_fill_price, message) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (getattr(order, 'order_id', ''), getattr(order, 'symbol', ''), getattr(order, 'exchange', ''), getattr(order, 'direction', ''), getattr(order, 'order_type', ''), getattr(order, 'quantity', 0), getattr(order, 'price', 0), response.status.value if hasattr(response.status, 'value') else str(response.status), response.broker_order_id, response.filled_quantity, response.avg_fill_price, response.message))
            self._conn.commit()
        except Exception as e:
            logging.getLogger("persistence").error(f"Log order failed: {e}")

    def get_orders(self, days=1):
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        return [dict(r) for r in self._conn.execute("SELECT * FROM orders WHERE created_at >= ? ORDER BY created_at DESC", [cutoff]).fetchall()]

    def audit_log(self, event_type, entity_id=None, details=None):
        self._conn.execute("INSERT INTO audit_log (event_type, entity_id, details) VALUES (?, ?, ?)", (event_type, entity_id, json.dumps(details) if details else None))
        self._conn.commit()

    def get_stats(self):
        try:
            return {"total_orders": self._conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0], "db_path": self.db_path}
        except Exception as e:
            return {"error": str(e)}
