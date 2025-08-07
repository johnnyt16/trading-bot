import os
import requests
from datetime import datetime
from loguru import logger
from typing import Optional, Dict, Any
import json

class AlertSystem:
    def __init__(self):
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.discord_webhook = os.getenv('DISCORD_WEBHOOK_URL')
        self.slack_webhook = os.getenv('SLACK_WEBHOOK_URL')
        
        self.alert_methods = []
        if self.telegram_token and self.telegram_chat_id:
            self.alert_methods.append('telegram')
            logger.info("Telegram alerts configured")
        if self.discord_webhook:
            self.alert_methods.append('discord')
            logger.info("Discord alerts configured")
        if self.slack_webhook:
            self.alert_methods.append('slack')
            logger.info("Slack alerts configured")
        
        if not self.alert_methods:
            logger.warning("No alert methods configured. Add credentials to .env file")
    
    def send_telegram(self, message: str) -> bool:
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            data = {
                'chat_id': self.telegram_chat_id,
                'text': message,
                'parse_mode': 'Markdown'
            }
            response = requests.post(url, data=data)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Telegram alert failed: {e}")
            return False
    
    def send_discord(self, message: str, embed: Optional[Dict] = None) -> bool:
        try:
            data = {"content": message}
            if embed:
                data["embeds"] = [embed]
            
            response = requests.post(self.discord_webhook, json=data)
            return response.status_code in [200, 204]
        except Exception as e:
            logger.error(f"Discord alert failed: {e}")
            return False
    
    def send_slack(self, message: str) -> bool:
        try:
            data = {"text": message}
            response = requests.post(self.slack_webhook, json=data)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Slack alert failed: {e}")
            return False
    
    def send_alert(self, message: str, alert_type: str = "info") -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        emoji_map = {
            "trade": "📈",
            "error": "❌",
            "warning": "⚠️",
            "success": "✅",
            "info": "ℹ️",
            "money": "💰"
        }
        
        emoji = emoji_map.get(alert_type, "📢")
        formatted_message = f"{emoji} [{timestamp}]\n{message}"
        
        for method in self.alert_methods:
            if method == 'telegram':
                self.send_telegram(formatted_message)
            elif method == 'discord':
                self.send_discord(formatted_message)
            elif method == 'slack':
                self.send_slack(formatted_message)
        
        logger.info(f"Alert sent: {message}")
    
    def send_trade_alert(self, trade_data: Dict[str, Any]) -> None:
        symbol = trade_data.get('symbol', 'N/A')
        side = trade_data.get('side', 'N/A')
        quantity = trade_data.get('quantity', 0)
        price = trade_data.get('price', 0)
        confidence = trade_data.get('confidence', 0)
        reasons = trade_data.get('reasons', [])
        
        message = f"""
🎯 *NEW TRADE EXECUTED*
Symbol: *{symbol}*
Side: *{side.upper()}*
Quantity: {quantity} shares
Price: ${price:.2f}
Total Value: ${quantity * price:.2f}
Confidence: {confidence}%
Reasons: {', '.join(reasons)}
"""
        
        self.send_alert(message, "trade")
    
    def send_pnl_alert(self, pnl_data: Dict[str, Any]) -> None:
        symbol = pnl_data.get('symbol', 'N/A')
        pnl = pnl_data.get('pnl', 0)
        pnl_percent = pnl_data.get('pnl_percent', 0)
        
        emoji = "💰" if pnl > 0 else "📉"
        status = "PROFIT" if pnl > 0 else "LOSS"
        
        message = f"""
{emoji} *POSITION CLOSED*
Symbol: *{symbol}*
P&L: ${pnl:.2f} ({pnl_percent:.2f}%)
Status: {status}
"""
        
        self.send_alert(message, "money" if pnl > 0 else "warning")
    
    def send_daily_summary(self, summary_data: Dict[str, Any]) -> None:
        total_trades = summary_data.get('total_trades', 0)
        winning_trades = summary_data.get('winning_trades', 0)
        losing_trades = summary_data.get('losing_trades', 0)
        daily_pnl = summary_data.get('daily_pnl', 0)
        win_rate = summary_data.get('win_rate', 0)
        
        emoji = "📊"
        if daily_pnl > 100:
            emoji = "🚀"
        elif daily_pnl > 0:
            emoji = "✅"
        elif daily_pnl < -100:
            emoji = "🔴"
        
        message = f"""
{emoji} *DAILY SUMMARY*
Date: {datetime.now().strftime('%Y-%m-%d')}
Total Trades: {total_trades}
Winning: {winning_trades} | Losing: {losing_trades}
Win Rate: {win_rate:.1f}%
Daily P&L: ${daily_pnl:.2f}
"""
        
        self.send_alert(message, "info")
    
    def send_error_alert(self, error_message: str) -> None:
        message = f"🚨 *ERROR ALERT*\n{error_message}"
        self.send_alert(message, "error")
    
    def send_system_status(self, status: str, details: str = "") -> None:
        emoji = "🟢" if status == "online" else "🔴"
        message = f"{emoji} *SYSTEM STATUS: {status.upper()}*\n{details}"
        self.send_alert(message, "info")