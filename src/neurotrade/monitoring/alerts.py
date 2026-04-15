"""Monitoring and Alerts"""
from __future__ import annotations
import logging
from datetime import datetime


class AlertManager:
    def __init__(self):
        self.logger = logging.getLogger("monitoring.alerts")

    def send(self, level, message, metadata=None):
        alert = {"level": level, "message": message, "metadata": metadata or {}, "timestamp": datetime.now().isoformat()}
        if level == "critical": self.logger.critical(f"ALERT: {message}")
        elif level == "warning": self.logger.warning(f"ALERT: {message}")
        else: self.logger.info(f"ALERT: {message}")
