# 🚀 Deployment Guide - DigitalOcean

## Why This Setup is Future-Proof:

✅ **Handles Current Bot** - Momentum trading
✅ **Options Trading** - Same infrastructure 
✅ **Multiple Strategies** - Just add Python files
✅ **Machine Learning** - Upgrade RAM as needed
✅ **Web Dashboard** - Nginx already installed
✅ **Database** - PostgreSQL ready
✅ **Scaling** - Easy to upgrade droplet

## Step 1: Create DigitalOcean Droplet

### Go to: https://www.digitalocean.com

1. Click "Create" → "Droplets"
2. Choose:
   - **Image**: Ubuntu 22.04 LTS
   - **Plan**: Basic
   - **Size**: $12/month (2GB RAM, 1 CPU, 50GB SSD)
   - **Region**: New York (closest to market servers)
   - **Authentication**: SSH keys (recommended) or Password

3. Click "Create Droplet"
4. Note your IP address: `XXX.XXX.XXX.XXX`

## Step 2: Connect to Your Server

```bash
ssh root@XXX.XXX.XXX.XXX
```

## Step 3: Run Setup Script

```bash
# Download setup script
wget https://raw.githubusercontent.com/YOUR_USERNAME/trading-bot/main/deploy/setup_server.sh
chmod +x setup_server.sh
./setup_server.sh
```

This installs:
- Python 3.10
- PostgreSQL (for future data storage)
- Redis (for future caching)
- Nginx (for future web dashboard)
- TA-Lib (for technical analysis)
- Monitoring tools

## Step 4: Deploy Your Bot

```bash
# Switch to tradingbot user
su - tradingbot

# Clone your repository
cd /opt/trading-bot
git clone https://github.com/YOUR_USERNAME/trading-bot.git .

# Run deployment script
bash deploy/deploy_bot.sh

# Edit your API keys
nano .env
# Add your actual Alpaca keys
```

## Step 5: Set Up Auto-Start Service

```bash
# Copy service file
sudo cp deploy/trading-bot.service /etc/systemd/system/

# Enable auto-start on boot
sudo systemctl enable trading-bot

# Start the bot
sudo systemctl start trading-bot

# Check status
sudo systemctl status trading-bot
```

## Step 6: Set Up Monitoring

```bash
# Create monitor service
sudo tee /etc/systemd/system/trading-bot-monitor.service > /dev/null <<EOF
[Unit]
Description=Trading Bot Monitor
After=trading-bot.service

[Service]
Type=simple
User=tradingbot
WorkingDirectory=/opt/trading-bot
ExecStart=/opt/trading-bot/venv/bin/python /opt/trading-bot/deploy/monitor.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Start monitor
sudo systemctl enable trading-bot-monitor
sudo systemctl start trading-bot-monitor
```

## Managing Your Bot:

### Start/Stop/Restart:
```bash
sudo systemctl start trading-bot
sudo systemctl stop trading-bot
sudo systemctl restart trading-bot
```

### View Logs:
```bash
# Live logs
sudo journalctl -u trading-bot -f

# Today's logs
sudo journalctl -u trading-bot --since today

# Check log files
tail -f /opt/trading-bot/logs/trading_*.log
```

### Update Code:
```bash
cd /opt/trading-bot
git pull
sudo systemctl restart trading-bot
```

### Check Performance:
```bash
cd /opt/trading-bot
./venv/bin/python main.py analyze
```

## Monitoring Dashboard:

### Option 1: Command Line
```bash
# SSH into server
ssh tradingbot@XXX.XXX.XXX.XXX

# Watch status
watch -n 60 './venv/bin/python main.py analyze'
```

### Option 2: Web Dashboard (Future)
- Already have Nginx installed
- Can add Flask/FastAPI dashboard later
- Access at: http://XXX.XXX.XXX.XXX

## Costs:

| Component | Monthly Cost |
|-----------|-------------|
| DigitalOcean Droplet | $12 |
| Total | $12/month |

Compare to:
- AWS EC2: ~$15-20/month
- Google Cloud: ~$15-25/month
- Running locally: $0 but unreliable

## Upgrading for Options Trading:

When ready for options/advanced features:

### Software (no changes needed):
- ✅ Same Python setup
- ✅ Same deployment process
- ✅ Just add new strategy files

### If needed for heavy ML:
```bash
# Resize droplet (no data loss)
# DigitalOcean Dashboard → Droplet → Resize
# Choose 4GB RAM ($24/month)
```

## Security:

✅ **Firewall** - Only SSH, HTTP, HTTPS open
✅ **Systemd** - Auto-restarts on crash
✅ **Logging** - 30-day retention
✅ **Monitoring** - Alerts on issues
✅ **Updates** - Ubuntu auto-security updates

## Backup Strategy:

```bash
# Backup database (when you add it)
pg_dump trading_bot > backup.sql

# Backup logs
tar -czf logs_backup.tar.gz logs/

# DigitalOcean automated backups
# Enable in Dashboard: +$2.40/month
```

## Your Bot Runs 24/7:

- ✅ **Market hours**: Actively trading
- ✅ **After hours**: Waiting, analyzing
- ✅ **Weekends**: Running backtests
- ✅ **Crashes**: Auto-restarts
- ✅ **Updates**: Quick deploy, minimal downtime

## Next Steps After Deployment:

1. **Week 1**: Monitor paper trading performance
2. **Week 2-4**: Tweak parameters based on results
3. **Month 2**: Add more strategies
4. **Month 3**: Consider options trading module
5. **Month 6**: Add web dashboard for remote monitoring

## Emergency Commands:

```bash
# If bot is stuck
sudo systemctl restart trading-bot

# If server is full
df -h  # Check disk
sudo apt-get clean

# If high CPU
htop  # Check processes

# Emergency stop all trading
sudo systemctl stop trading-bot
```

## This Setup Handles Everything:

- ✅ Current momentum bot
- ✅ Future options trading
- ✅ Multiple strategies
- ✅ Machine learning models
- ✅ Real-time data feeds
- ✅ Web dashboard
- ✅ Database storage
- ✅ Alert system

**One $12/month droplet runs it all!**