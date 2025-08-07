# 🖥️ Terminal Output Examples

## Bot Startup
```
🚀 Initializing Crypto Trading Bot...
✅ Bot initialized successfully
🤖 Bot is now active and scanning for new listings...
💰 Max trade amount: €5.0
🔄 Checking every 10 seconds
📈 Stop loss: 5.0% | Trailing stop: 3.0%
------------------------------------------------------------
📊 Monitoring 247 markets for new listings
🕐 14:23:15 | ✅ Bot running | 👀 Scanning for new listings... | Scan #1
```

## Normal Operation (No New Listings)
```
🕐 14:24:15 | ✅ Bot running | 👀 Scanning for new listings... | Scan #7
🕐 14:25:15 | ✅ Bot running | 👀 Scanning for new listings... | Scan #13
🕐 14:26:15 | ✅ Bot running | 👀 Scanning for new listings... | Scan #19
```

## New Listing Detection & Trading
```
🚨 NEW LISTING DETECTED: NEWCOIN-EUR
🔍 Analyzing NEWCOIN-EUR...
📊 NEWCOIN-EUR | Price: €0.001250 | Volume: €125.50
💸 EXECUTING BUY ORDER: €5.0 of NEWCOIN-EUR
✅ BUY SUCCESS: NEWCOIN-EUR at €0.001250
🎯 Starting monitoring with trailing stop-loss...

🕐 14:27:15 | ✅ Bot running | 📊 1 active trades | Scan #25
```

## Price Movements & Updates
```
📈 NEWCOIN-EUR NEW HIGH: €0.001375 (+10.0%) | Stop: €0.001334
📈 NEWCOIN-EUR NEW HIGH: €0.001500 (+20.0%) | Stop: €0.001455
📈 NEWCOIN-EUR NEW HIGH: €0.001625 (+30.0%) | Stop: €0.001576
```

## Profitable Sale (Trailing Stop)
```
🎯 TRAILING STOP TRIGGERED: NEWCOIN-EUR
💰 Sell at €0.001576 | Profit: 26.08%
✅ SELL SUCCESS: NEWCOIN-EUR position closed with profit!
```

## Loss Sale (Stop Loss)
```
🛑 STOP LOSS TRIGGERED: NEWCOIN-EUR
💸 Sell at €0.001188 | Loss: -4.96%
✅ SELL SUCCESS: NEWCOIN-EUR position closed
```

## Bot Shutdown
```
🛑 SHUTDOWN REQUESTED - Cleaning up safely...
🔄 Closing all active positions...
📊 Stopping 2 active trades...
🛑 Closing position: COIN1-EUR
🛑 Closing position: COIN2-EUR
💾 Market data saved
✅ Bot shutdown complete
```

## Error Handling
```
❌ Could not fetch ticker data for BADCOIN-EUR
⚠️ Volume too low (€15.50 < €50.00), skipping...
❌ BUY FAILED: Could not execute order for FAILCOIN-EUR
🚨 ERROR in main loop: Connection timeout
```

## Key Features of Terminal Output:
- **🤖 Real-time status** - See exactly what the bot is doing
- **📊 Trade details** - Price, volume, profit/loss percentages  
- **🎯 Action alerts** - Clear notifications for buy/sell events
- **⏰ Heartbeat** - Regular status updates every minute
- **🛑 Safe shutdown** - Clear cleanup progress
- **❌ Error visibility** - Problems are immediately visible

The terminal provides live feedback while all detailed information is still logged to `logs/trading.log` for permanent record keeping.