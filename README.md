# AI-Miaoda-Application-NueroTradeSystem

**Institutional-grade automated trading system for China A-Share markets**

> ⚠️ **IMPORTANT**: This system requires a licensed brokerage account with A-Share trading permission. Direct exchange access is not permitted without proper regulatory authorization.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    NeuroTrade System Architecture                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐        │
│  │   Market     │───▶│    AI        │───▶│   Order      │        │
│  │   Data       │    │   Decision   │    │   Executor   │        │
│  │   Feed       │    │   Engine     │    │              │        │
│  │  (Level-2)   │    │ (Strategy)   │    │  (CTP/XTP)   │        │
│  └──────────────┘    └──────────────┘    └──────────────┘        │
│                            │                   │                   │
│                            ▼                   ▼                   │
│                      ┌──────────────┐    ┌──────────────┐        │
│                      │    Risk      │    │   Position   │        │
│                      │   Manager    │    │   Manager    │        │
│                      │ (Pre/Post)   │    │              │        │
│                      └──────────────┘    └──────────────┘        │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Features

| Feature | Status | Description |
|---------|--------|-------------|
| Real-time Market Data | ✅ | SSE/SZSE Level-2 market data feed |
| Risk Management | ✅ | Pre-trade and post-trade risk controls |
| Position Tracking | ✅ | Real-time position and P&L monitoring |
| Order Execution | ✅ | CTP/XTP protocol support via broker API |
| AI Decision Engine | ✅ | Strategy-based signal generation |
| Paper Trading | ✅ | Simulator for strategy validation |
| Audit Logging | ✅ | Full audit trail of all operations |

## Security Design

```
Defense Layers:
1. Network: Encrypted + Firewall + VPN only
2. Auth: API keys in environment variables (never in code)
3. Risk Pre-Check: Every order validated against limits BEFORE sending
4. Position Limits: Hard caps on single stock / sector / total
5. Circuit Breakers: Auto-halt on abnormal market conditions
6. Human-in-Loop: Critical decisions require approval
```

## Installation

```bash
git clone https://github.com/sunxintalent/AI-Miaoda-Application-NueroTradeSystem.git
cd AI-Miaoda-Application-NueroTradeSystem
pip install -e ".[dev]"

# Configure broker credentials
cp config/broker.example.yaml config/broker.yaml
# Edit config/broker.yaml with your broker API credentials
```

## Configuration

### Environment Variables (Required)

```bash
# Broker API Credentials (from your brokerage)
export BROKER_APP_ID="your_app_id"
export BROKER_AUTH_CODE="your_auth_code"
export BROKER_USER_ID="your_user_id"
export BROKER_PASSWORD="your_password"
export BROKER_FRONT_URL="tcp://broker.front.url:port"

# Data Feed (optional, from data vendor)
export WIND_API_KEY="your_wind_key"  # or similar

# System
export NEUROTRADE_MODE="paper"  # paper | live
export NEUROTRADE_LOG_LEVEL="INFO"
```

## Usage

### Paper Trading (Recommended First)

```bash
export NEUROTRADE_MODE=paper
python -m src.core.main --mode paper
```

### Live Trading

```bash
export NEUROTRADE_MODE=live
python -m src.core.main --mode live --approve-critical
```

### Health Check

```bash
python -m src.core.main doctor
```

## Project Structure

```
src/
├── core/           # Core engine (main entry, config)
├── data/           # Market data feed (SSE/SZSE Level-2)
├── execution/      # Order execution layer (CTP/XTP adapters)
├── risk/           # Risk management (pre/post checks)
├── strategies/     # Trading strategies
├── ai/             # AI decision engine
├── monitoring/     # Real-time monitoring
└── persistence/    # Database and state management
```

## Risk Controls

| Control | Trigger | Action |
|---------|---------|--------|
| Single Stock Limit | >10% of float | Reject order |
| Daily Loss Limit | -2% of portfolio | Halt trading |
| Position Concentration | >20% single stock | Warning + approval |
| Volatility Circuit | >5% index drop | Auto-halt all orders |
| API Error Rate | >5% failure rate | Suspend trading |

## Exchange Protocols

| Protocol | Exchange | Use Case |
|----------|----------|----------|
| **CTP** | All (SHFE/SZSE/DCE/CZCE) | Futures + Stocks |
| **XTP** | SSE/SZSE | A-Share trading |
| **Level-2** | SSE/SZSE | Real-time market data |

> **Note**: Real trading requires a licensed brokerage. System connects via broker's CTP/XTP gateway.

## Backtesting

```python
from src.strategies import MeanReversion
from src.backtest import BacktestEngine

strategy = MeanReversion()
engine = BacktestEngine(strategy=strategy, start="2024-01-01", end="2024-12-31")
result = engine.run()
print(result.summary())
```

## Monitoring

```bash
# View real-time positions
python -m src.monitoring.cli positions

# View P&L
python -m src.monitoring.cli pnl --today

# View orders
python -m src.monitoring.cli orders --status=pending
```

## Disclaimer

⚠️ **IMPORTANT**: This software is provided for educational and research purposes. Automated trading in China's A-Share market requires proper regulatory authorization. The authors are not responsible for any financial losses incurred through the use of this software. **Always use paper trading mode first and monitor all decisions.**

## License

MIT License

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Submit a pull request
5. All trading-related changes require risk team review
