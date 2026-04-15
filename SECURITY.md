# Security Policy

## API Credentials

**NEVER commit API credentials to version control.**

### Required Environment Variables

```bash
# Broker API (Required for live trading)
export BROKER_FRONT_URL="tcp://your.broker.com:41205"
export BROKER_APP_ID="your_app_id"
export BROKER_AUTH_CODE="your_auth_code"
export BROKER_USER_ID="your_user_id"
export BROKER_PASSWORD="your_password"

# Data Feed (Optional)
export DATA_API_KEY="your_data_key"

# System
export NEUROTRADE_MODE="paper"  # or "live"
```

## Security Checklist

- [ ] API credentials in environment variables, NOT in code
- [ ] Database file in `/tmp/` or secure location (not in repo)
- [ ] No hardcoded IP addresses or URLs
- [ ] All orders pass risk checks before execution
- [ ] Audit log enabled for all operations
- [ ] Paper trading tested before live mode
- [ ] Position limits configured appropriately

## Reporting Security Issues

If you discover a security vulnerability, please report it privately.
