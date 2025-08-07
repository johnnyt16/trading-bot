#!/bin/bash
# Server setup script for Ubuntu 22.04 on DigitalOcean
# Run this after creating your droplet

set -e  # Exit on error

echo "🚀 Setting up Trading Bot Server..."

# Update system
echo "📦 Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install Python and essentials
echo "🐍 Installing Python 3.10..."
sudo apt-get install -y python3.10 python3.10-venv python3-pip
sudo apt-get install -y git curl wget build-essential

# Install TA-Lib dependencies (for future technical analysis)
echo "📊 Installing TA-Lib..."
sudo apt-get install -y libta-lib0-dev
wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
tar -xzf ta-lib-0.4.0-src.tar.gz
cd ta-lib/
./configure --prefix=/usr
make
sudo make install
cd ..
rm -rf ta-lib ta-lib-0.4.0-src.tar.gz

# Install PostgreSQL (for future data storage)
echo "🗄️ Installing PostgreSQL..."
sudo apt-get install -y postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Install Redis (for future caching/queues)
echo "💾 Installing Redis..."
sudo apt-get install -y redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Install monitoring tools
echo "📈 Installing monitoring tools..."
sudo apt-get install -y htop tmux screen supervisor

# Create app user
echo "👤 Creating app user..."
sudo useradd -m -s /bin/bash tradingbot || true
sudo usermod -aG sudo tradingbot

# Create app directory
echo "📁 Setting up app directory..."
sudo mkdir -p /opt/trading-bot
sudo chown -R tradingbot:tradingbot /opt/trading-bot

# Setup log directory
sudo mkdir -p /var/log/trading-bot
sudo chown -R tradingbot:tradingbot /var/log/trading-bot

# Install Nginx (for future web dashboard)
echo "🌐 Installing Nginx..."
sudo apt-get install -y nginx
sudo systemctl start nginx
sudo systemctl enable nginx

# Setup firewall
echo "🔒 Configuring firewall..."
sudo ufw allow 22    # SSH
sudo ufw allow 80    # HTTP (future dashboard)
sudo ufw allow 443   # HTTPS (future dashboard)
sudo ufw --force enable

echo "✅ Server setup complete!"
echo ""
echo "Next steps:"
echo "1. Clone your repository to /opt/trading-bot"
echo "2. Run deploy_bot.sh to install the bot"
echo "3. Configure your .env file"
echo "4. Start the bot with systemctl"