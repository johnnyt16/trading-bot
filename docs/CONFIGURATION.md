# Configuration Guide

## Environment Variables (.env)

### Required Settings

```bash
# Alpaca API Credentials
ALPACA_API_KEY=PKxxxxxxxxxxxxxx
ALPACA_SECRET_KEY=xxxxxxxxxxxxxxxxxxxxxxxx
ALPACA_BASE_URL=https://paper-api.alpaca.markets
```

Get these from: https://app.alpaca.markets/paper/dashboard/overview

### Trading Parameters

```bash
# Position Sizing
MAX_POSITION_SIZE=0.05      # Max 5% of portfolio per trade
MAX_DAILY_LOSS=0.05         # Stop trading after 5% daily loss

# Exit Points
STOP_LOSS_PERCENT=0.03      # Exit at -3% loss
TAKE_PROFIT_PERCENT=0.05    # Exit at +5% profit

# Entry Requirements  
MIN_CONFIDENCE_SCORE=0.6    # Minimum 60% confidence to trade
RISK_REWARD_RATIO=2.0       # Target 2:1 reward/risk

# Stocks to Monitor
WATCHLIST=TSLA,NVDA,AMD,AAPL,MSFT,META,GOOGL,AMZN
```

### Optional: Alert Configuration

```bash
# Telegram Alerts
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Discord Alerts
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...

# Database (defaults to SQLite)
DATABASE_URL=sqlite:///trading_bot.db
```

## Adjusting Parameters

### Conservative Settings
```bash
MIN_CONFIDENCE_SCORE=0.75   # Fewer trades, higher quality
STOP_LOSS_PERCENT=0.02      # Tighter stop loss
MAX_POSITION_SIZE=0.03      # Smaller positions
```

### Aggressive Settings
```bash
MIN_CONFIDENCE_SCORE=0.55   # More trades
TAKE_PROFIT_PERCENT=0.08    # Higher profit target
MAX_POSITION_SIZE=0.10      # Larger positions
```

### Best Times to Trade
- **9:30-10:30 AM EST**: Market open, highest volatility
- **3:00-4:00 PM EST**: Power hour, increased activity
- **Avoid 12:00-1:00 PM EST**: Lunch lull, low volume

## Command Line Options

```bash
# Backtest with custom settings
python main.py backtest --symbols TSLA NVDA --capital 5000 --period 6mo

# Paper trade with debug logging
python main.py paper --log-level DEBUG

# Analyze specific date range
python main.py analyze --start 2024-01-01 --end 2024-01-31
```

## File Locations

- **Logs**: `logs/trading_YYYY-MM-DD.log`
- **Backtest Results**: `backtest_results/backtest_*.json`
- **Database**: `trading_bot.db` (SQLite)
- **Configuration**: `.env` (root directory)