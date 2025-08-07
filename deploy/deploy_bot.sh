#!/bin/bash
# Deploy the trading bot to the server
# Run this as the tradingbot user

set -e

echo "🚀 Deploying Trading Bot..."

# Navigate to app directory
cd /opt/trading-bot

# Pull latest code (or clone if first time)
if [ -d ".git" ]; then
    echo "📥 Pulling latest code..."
    git pull origin main
else
    echo "📥 Cloning repository..."
    git clone https://github.com/YOUR_USERNAME/trading-bot.git .
fi

# Create virtual environment
echo "🐍 Setting up Python environment..."
python3.10 -m venv venv

# Activate venv and install dependencies
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your API keys!"
fi

# Create necessary directories
mkdir -p logs data backtest_results

# Set up log rotation
echo "📁 Setting up log rotation..."
sudo tee /etc/logrotate.d/trading-bot > /dev/null <<EOF
/opt/trading-bot/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 tradingbot tradingbot
    sharedscripts
    postrotate
        systemctl reload trading-bot || true
    endscript
}
EOF

echo "✅ Deployment complete!"
echo ""
echo "To start the bot:"
echo "  sudo systemctl start trading-bot"
echo "  sudo systemctl status trading-bot"
echo ""
echo "To view logs:"
echo "  sudo journalctl -u trading-bot -f"