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
cp .env.example .env
# Edit .env with your Alpaca API keys
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

- 📁 [Project Structure](docs/PROJECT_STRUCTURE.md) - How the code is organized
- 🚀 [Deployment Guide](docs/DEPLOYMENT.md) - Deploy to DigitalOcean for 24/7 operation
- 📊 [Trading Strategy](docs/STRATEGY.md) - How the momentum strategy works
- 🔧 [Configuration](docs/CONFIGURATION.md) - Settings and parameters


## Project Status

✅ **Working**: Basic momentum strategy with paper trading
🚧 **In Progress**: Optimization and testing
📅 **Planned**: Options trading, ML predictions, web dashboard

## Command Reference

| Command | Description |
|---------|-------------|
| `python main.py test` | Test Alpaca connection |
| `python main.py backtest` | Run historical backtest |
| `python main.py paper` | Start paper trading |
| `python main.py analyze` | Show performance metrics |

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