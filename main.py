#!/usr/bin/env python3
"""
main.py - Simplified main file for GPT-5 autonomous trading
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
sys.path.append(str(Path(__file__).parent))

from src.ai_brain.gpt5_trading_system import GPT5TradingBrain
from loguru import logger

async def main():
    """
    Main function - GPT-5 runs everything autonomously
    """
    try:
        # Initialize the AI brain
        logger.info("Initializing GPT-5 Trading System...")
        brain = GPT5TradingBrain()
        
        logger.info("🚀 GPT-5 Autonomous Trading Started")
        logger.info("Target: $1,000 → $10,000")
        
        # The main trading loop
        while True:
            # Check market status
            clock = brain.alpaca.get_clock()
            current_time = datetime.now()
            current_hour = current_time.hour
            
            # Extended hours: 4 AM - 9:30 AM and 4 PM - 8 PM ET
            is_premarket = (current_hour >= 4 and current_hour < 9) or (current_hour == 9 and current_time.minute < 30)
            is_afterhours = current_hour >= 16 and current_hour < 20
            is_extended = is_premarket or is_afterhours
            
            if not clock.is_open and not is_extended:
                next_open = clock.next_open.strftime('%Y-%m-%d %H:%M:%S ET')
                logger.info(f"Market closed. Next open: {next_open}")
                logger.info("Waiting 5 minutes...")
                await asyncio.sleep(300)  # 5 minutes
                continue
            
            if is_premarket:
                logger.info("🌅 PRE-MARKET TRADING (4 AM - 9:30 AM ET)")
                logger.info("Prime time for news reactions and gap plays!")
            elif is_afterhours:
                logger.info("🌙 AFTER-HOURS TRADING (4 PM - 8 PM ET)")
                logger.info("Earnings reactions and news catalysts!")
            elif clock.is_open:
                logger.info("📈 Regular market hours active")
            
            # GPT-5 does everything
            logger.info("🔍 Scanning for opportunities...")
            opportunities = await brain.autonomous_market_scan()
            
            # Analyze and trade top opportunities
            for opp in opportunities[:3]:
                analysis = await brain.deep_analysis(opp['symbol'])
                
                if analysis['decision'] == 'GO':
                    await brain.execute_trade(analysis)
            
            # Manage positions
            await brain.manage_positions()
            
            # Learn (every hour)
            if datetime.now().minute == 0:
                await brain.learn_and_adapt()
            
            # Wait 30 seconds before next scan
            await asyncio.sleep(30)
            
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")

if __name__ == "__main__":
    asyncio.run(main())