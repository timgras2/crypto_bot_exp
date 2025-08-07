# 🛡️ SAFETY CHECKLIST - READ BEFORE TRADING

## ⚠️ CRITICAL WARNINGS

- **REAL MONEY**: This bot trades with real funds on live markets
- **HIGH RISK**: New token listings are extremely volatile  
- **NO GUARANTEES**: You can lose money quickly
- **AUTOMATION**: Bot executes trades without human confirmation

## 📋 Pre-Launch Safety Review

### ✅ Configuration Review

**Trading Parameters** (in `.env` file):
- [ ] `MAX_TRADE_AMOUNT` set to safe amount (recommend: 5.0 EUR for testing)
- [ ] `MIN_PROFIT_PCT` appropriate for risk tolerance (default: 5.0%)
- [ ] `TRAILING_PCT` set conservatively (default: 3.0%)
- [ ] `CHECK_INTERVAL` reasonable (default: 10 seconds)

**API Configuration**:
- [ ] Valid Bitvavo API key and secret configured
- [ ] API permissions limited to trading only (not withdrawal)
- [ ] Using official Bitvavo API URL

### ✅ Account Safety

**Bitvavo Account**:
- [ ] Sufficient EUR balance for trading (more than MAX_TRADE_AMOUNT)
- [ ] 2FA enabled on account
- [ ] API withdrawal permissions DISABLED
- [ ] Only test amounts in account for initial runs

### ✅ Technical Safety

**Bot Environment**:
- [ ] All tests passing (`python -m pytest tests/`)
- [ ] Bot starts without errors
- [ ] Log files being created properly
- [ ] Stable internet connection
- [ ] Computer will remain on during trading

### ✅ Recommended Test Sequence

1. **Start with tiny amounts**: Set `MAX_TRADE_AMOUNT=1.0`
2. **Monitor first trades**: Watch logs carefully
3. **Check trade execution**: Verify buy/sell orders work
4. **Verify stop-loss**: Ensure safety mechanisms work
5. **Gradually increase**: Only after successful test runs

## 🚨 EMERGENCY STOP

**To stop the bot immediately**:
- Press `Ctrl+C` in the terminal
- The bot will gracefully close all positions
- Check Bitvavo account to verify all trades closed

## 📞 SUPPORT

If something goes wrong:
1. Stop the bot immediately
2. Check `logs/trading.log` for errors
3. Verify account status on Bitvavo
4. Do not restart until issue is understood

---
**Remember**: Start small, monitor closely, and never risk more than you can afford to lose.