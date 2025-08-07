# Logs Directory

This directory contains trading bot log files:

- `trading.log` - Main bot activity log
- `trades/` - Individual trade logs (if implemented)
- `errors/` - Error logs for debugging

## Log Rotation

Logs can get large over time. Consider implementing log rotation:
- Daily rotation for active trading
- Keep last 30 days of logs
- Archive older logs for analysis