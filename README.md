# Trading Bot - Momentum Strategy for Alpaca

A Python trading bot that uses momentum strategies to trade stocks automatically using Alpaca's API.

## Quick Start

### 1. Setup

```bash
# Install dependencies
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure API keys
# Create .env and edit with your keys
cat > .env << 'EOF'
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...
ALPACA_API_KEY=PK...
ALPACA_SECRET_KEY=...
ALPACA_BASE_URL=https://paper-api.alpaca.markets
MAX_POSITION_SIZE=0.05
STOP_LOSS_PERCENT=0.03
TAKE_PROFIT_PERCENT=0.05
MIN_CONFIDENCE_SCORE=0.6
DATABASE_URL=sqlite:///trading_bot.db
EOF
```

### 2. Test Connection

```bash
python main.py test
```

### 3. Run Backtest

```bash
python main.py backtest
```

### 4. Start Paper Trading

```bash
python main.py paper
```

## Features

- **Momentum Trading**: Identifies stocks with strong upward movement
- **Risk Management**: Automatic stop-loss and take-profit orders
- **Paper Trading**: Test with $100k virtual money
- **Backtesting**: Test strategies on historical data
- **Logging**: Detailed logs of all trading activity

## Documentation

- Project docs are coming soon. For now, see the codebase and comments.

## Project Status

✅ **Working**: Basic momentum strategy with paper trading
🚧 **In Progress**: Optimization and testing
📅 **Planned**: Options trading, ML predictions, web dashboard

## Command Reference

| Command                   | Description              |
| ------------------------- | ------------------------ |
| `python main.py test`     | Test Alpaca connection   |
| `python main.py backtest` | Run historical backtest  |
| `python main.py paper`    | Start paper trading      |
| `python main.py analyze`  | Show performance metrics |

## Configuration (.env)

```bash
# Alpaca API (required)
ALPACA_API_KEY=your_key
ALPACA_SECRET_KEY=your_secret

# Trading Parameters
MAX_POSITION_SIZE=0.05      # 5% per trade
STOP_LOSS_PERCENT=0.03       # 3% stop loss
TAKE_PROFIT_PERCENT=0.05     # 5% take profit
MIN_CONFIDENCE_SCORE=0.6     # 60% minimum confidence
```

## License

MIT
