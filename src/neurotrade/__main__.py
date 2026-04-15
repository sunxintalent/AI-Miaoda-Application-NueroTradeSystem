"""Main entry point for NeuroTrade CLI"""
from __future__ import annotations
import asyncio
import logging
import os
import signal
import sys

from .core.engine import NeuroTradeEngine, TradingConfig, run_doctor


def load_config() -> TradingConfig:
    mode = os.environ.get("NEUROTRADE_MODE", "paper")
    symbols_env = os.environ.get("NEUROTRADE_SYMBOLS", "600519,000858")
    symbols = [s.strip() for s in symbols_env.split(",") if s.strip()]
    exchanges = []
    for s in symbols:
        if s.startswith(("6", "5")) and "SSE" not in exchanges:
            exchanges.append("SSE")
        elif s.startswith(("0", "1", "3")) and "SZSE" not in exchanges:
            exchanges.append("SZSE")
    return TradingConfig(
        mode=mode, symbols=symbols, exchanges=exchanges if exchanges else ["SSE", "SZSE"],
        broker_front_url=os.environ.get("BROKER_FRONT_URL", ""),
        broker_app_id=os.environ.get("BROKER_APP_ID", ""),
        broker_auth_code=os.environ.get("BROKER_AUTH_CODE", ""),
        broker_user_id=os.environ.get("BROKER_USER_ID", ""),
        broker_password=os.environ.get("BROKER_PASSWORD", ""),
        data_provider=os.environ.get("DATA_PROVIDER", "mock"),
        log_level=os.environ.get("NEUROTRADE_LOG_LEVEL", "INFO"),
    )


async def async_main(mode=None, symbols=None):
    if mode == "doctor":
        result = await run_doctor()
        print("\n=== NeuroTrade System Health Check ===")
        for name, ok, detail in result["checks"]:
            print(f"  {'PASS' if ok else 'FAIL'} {name}: {detail}")
        print(f"\n{result['passed']}/{result['total']} checks passed")
        return 0
    config = load_config()
    if mode: config.mode = mode
    if symbols: config.symbols = symbols
    engine = NeuroTradeEngine(config)
    for sig in (signal.SIGTERM, signal.SIGINT):
        asyncio.get_event_loop().add_signal_handler(sig, lambda: asyncio.create_task(engine.stop()))
    try:
        await engine.start()
    except KeyboardInterrupt:
        await engine.stop()
    return 0


def main():
    import argparse
    parser = argparse.ArgumentParser(description="NeuroTrade - China A-Share Automated Trading System")
    parser.add_argument("command", nargs="?", choices=["doctor", "start"])
    parser.add_argument("--mode", "-m", choices=["paper", "live"])
    parser.add_argument("--symbols", "-s", nargs="+")
    args = parser.parse_args()
    if args.command == "doctor":
        return asyncio.run(async_main(mode="doctor"))
    return asyncio.run(async_main(mode=args.mode, symbols=args.symbols))


if __name__ == "__main__":
    sys.exit(main())
