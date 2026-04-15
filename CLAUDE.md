# CLAUDE.md - AI Agent Guidance

## System Overview

AI-Miaoda-Application-NueroTradeSystem is an institutional-grade automated trading system for China A-Share markets (SSE/SZSE). This is a **security-critical financial system** — every line of code must be reviewed with risk awareness.

## Architecture Principles

1. **Risk First** - Every order passes through multi-layer risk checks
2. **Audit Everything** - Full logging of all decisions and executions
3. **Fail Safe** - System halts on critical errors, never autodiscusses
4. **Minimal Blast Radius** - Position limits, circuit breakers, automatic stops

## Security Rules (Absolute)

- NEVER commit API keys, tokens, or credentials
- NEVER disable risk controls in production
- NEVER allow orders outside pre-defined position limits
- All broker credentials must be in environment variables or secure vault
- Order quantity and price must always be validated against limits

## Exchange Connectivity

China A-Shares use **CTP/XTP protocols**. Real trading requires:
1. A brokerage account with trading permission
2. Broker-provided API credentials (app_id, auth_code, user_id, password)
3. Broker's trading system address (front_url)

**NEVER attempt to connect to exchanges directly** without brokerage intermediary.

## When Making Changes

1. All strategy changes require backtesting validation
2. Risk module changes require sign-off
3. Test in paper-trading mode first
4. Monitor all positions in real-time
5. Log all order decisions with full context

## Testing

```bash
# Paper trading (no real orders)
pytest tests/ -v

# Backtesting
python -m examples.backtest --strategy mean_reversion --period 2024

# Risk validation
python -m risk.validate --check-all
```

## Key Contacts

- Exchange: SSE (www.sse.com.cn), SZSE (www.szse.cn)
- Data Provider: Licensed broker or data vendor
- Risk Owner: Human oversight required at all times
