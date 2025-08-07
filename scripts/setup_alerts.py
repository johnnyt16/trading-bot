#!/usr/bin/env python3
"""
Setup and test alert channels
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils import AlertSystem
from dotenv import load_dotenv

load_dotenv()

def test_alerts():
    print("Testing alert system...")
    print("="*50)
    
    alert_system = AlertSystem()
    
    if not alert_system.alert_methods:
        print("❌ No alert methods configured!")
        print("\nTo set up alerts, add one of these to your .env file:")
        print("\nTelegram:")
        print("  TELEGRAM_BOT_TOKEN=your_bot_token")
        print("  TELEGRAM_CHAT_ID=your_chat_id")
        print("\nDiscord:")
        print("  DISCORD_WEBHOOK_URL=your_webhook_url")
        print("\nSlack:")
        print("  SLACK_WEBHOOK_URL=your_webhook_url")
        return False
    
    print(f"✅ Alert methods configured: {', '.join(alert_system.alert_methods)}")
    
    print("\nSending test alerts...")
    
    alert_system.send_alert("🧪 Test alert from Trading Bot", "info")
    
    alert_system.send_trade_alert({
        'symbol': 'TEST',
        'side': 'buy',
        'quantity': 100,
        'price': 150.50,
        'confidence': 75,
        'reasons': ['Test signal', 'Demo trade']
    })
    
    alert_system.send_pnl_alert({
        'symbol': 'TEST',
        'pnl': 250.00,
        'pnl_percent': 5.5
    })
    
    alert_system.send_daily_summary({
        'total_trades': 10,
        'winning_trades': 7,
        'losing_trades': 3,
        'daily_pnl': 500.00,
        'win_rate': 70
    })
    
    print("\n✅ Test alerts sent! Check your configured channels.")
    return True

if __name__ == "__main__":
    if test_alerts():
        print("\nAlert system is working!")
    else:
        print("\nPlease configure alerts in .env file")