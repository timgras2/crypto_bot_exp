# 🚀 Crypto Bot Quick Start Guide

## 📦 ONE-TIME SETUP

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure API credentials**:
   ```bash
   cp .env.example .env
   # Edit .env with your Bitvavo API key and secret
   ```

3. **⚠️ SAFETY FIRST**: Read `SAFETY_CHECKLIST.md`

## 🏃 QUICK LAUNCH

### Windows:
```bash
# Double-click start_bot.bat
# OR run in command prompt:
python start_bot.py
```

### Linux/Mac:
```bash
chmod +x start_bot.sh
./start_bot.sh
# OR:
python3 start_bot.py
```

## 🛑 STOPPING THE BOT

- Press `Ctrl+C` in the terminal
- Bot will safely close all positions
- Check `logs/trading.log` for shutdown confirmation

## 📊 MONITORING

**Real-time Terminal**: Watch live activity with emojis and clear status updates
- 🤖 Startup and configuration display
- 👀 Periodic scanning status (every minute)
- 🚨 New listing alerts with price/volume data
- 📈 Price movement updates (new highs)
- 💰 Trade execution confirmations
- 🎯 Profit/loss on sales

**Detailed Logs**: Check `logs/trading.log` for permanent records
**Bitvavo Account**: Monitor your account on bitvavo.com

See `TERMINAL_OUTPUT_EXAMPLE.md` for what to expect!

## ⚙️ KEY SETTINGS (in .env file)

| Setting | Default | Description |
|---------|---------|-------------|
| `MAX_TRADE_AMOUNT` | 5.0 | EUR per trade (START SMALL!) |
| `MIN_PROFIT_PCT` | 5.0 | Stop loss percentage |
| `TRAILING_PCT` | 3.0 | Trailing stop percentage |
| `CHECK_INTERVAL` | 10 | Seconds between checks |
| `OPERATOR_ID` | 1001 | Required by Bitvavo API (compliance) |

## 🚨 WHAT THE BOT DOES

### **First Run (Safe Baseline Establishment)**
1. **Establishes baseline** of existing markets (NO trading)
2. **Saves market data** to `data/previous_markets.json`
3. **Starts monitoring** for truly NEW listings

### **Normal Operation** 
1. **Scans** for new token listings every 10 seconds
2. **Buys** new tokens immediately (€5 default)  
3. **Monitors** price with trailing stop-loss
4. **Sells** automatically when stop-loss triggers

⚖️ **SAFETY**: First run will NOT trade - it only establishes what markets already exist!

## ❓ TROUBLESHOOTING

**Bot won't start?**
- Check `.env` file exists and has valid API credentials
- Run `python -m pytest tests/` to verify installation

**No trades happening?**
- New listings are rare - be patient
- Check logs for any error messages

**Bot crashed?**
- Check `logs/trading.log` for error details
- Verify account balance and API permissions

## 📞 SUPPORT

1. Check `logs/trading.log` for errors
2. Verify all tests pass: `python -m pytest tests/`
3. Review `SAFETY_CHECKLIST.md`
4. Ensure stable internet connection

---
**Remember**: This trades with REAL MONEY. Start small and monitor closely!