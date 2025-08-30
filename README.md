# Crypto Trading Bot

A cryptocurrency trading bot for the Bitvavo exchange that automatically detects new token listings and trades them with trailing stop-loss protection.

## 🚀 Quick Start

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your Bitvavo API credentials
   ```

3. **Run the bot**
   ```bash
   python scripts/start_bot.py
   ```

## 📋 Features

- **New Listing Detection** - Automatically detects newly added trading pairs
- **Automated Trading** - Places market buy orders with configurable amounts
- **Trailing Stop-Loss** - Dynamic profit protection that adjusts with price increases
- **State Recovery** - Resumes monitoring trades after bot restarts
- **Risk Management** - Configurable trade limits and stop-loss percentages
- **Rate Limiting** - Respects exchange API limits
- **Comprehensive Logging** - Detailed activity logs for monitoring

## ⚙️ Configuration

Required environment variables:
- `BITVAVO_API_KEY` - Your Bitvavo API key
- `BITVAVO_API_SECRET` - Your Bitvavo API secret

Optional parameters (see `.env.example` for all options):
- `MAX_TRADE_AMOUNT=10.0` - Maximum EUR per trade
- `MIN_PROFIT_PCT=5.0` - Stop loss percentage
- `TRAILING_PCT=3.0` - Trailing stop percentage

## 🧪 Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test
python -m pytest tests/test_config.py -v
```

## 📁 Project Structure

```
├── src/                    # Core bot code
├── tests/                  # Unit tests
├── scripts/                # Utility scripts
├── docs/                   # Documentation
├── requirements.txt        # Dependencies
└── .env.example           # Configuration template
```

## 🔧 Utility Scripts

- `scripts/start_bot.py` - Start the trading bot
- `scripts/review_trades.py` - Analyze trading performance
- `scripts/sell_small_holdings.py` - Clean up small positions

## 📚 Documentation

- [Quick Start Guide](docs/QUICKSTART.md) - Detailed setup instructions
- [Safety Checklist](docs/SAFETY_CHECKLIST.md) - Pre-trading verification
- [API Updates](docs/BITVAVO_API_UPDATE.md) - Recent API changes

## 🚨 Risk Warning

**This bot trades with real money. Always:**
- Test in a safe environment first
- Start with small amounts
- Monitor the bot actively
- Review the safety checklist before trading

## 🌟 Advanced Features

For additional features like asset protection and sentiment analysis, check out the feature branches:
- `feature/asset-protection-strategy` - DCA buying and profit taking
- `feature/social-media-sentiment-analysis` - Reddit sentiment integration

## 📄 License

This project is for educational purposes. Use at your own risk.