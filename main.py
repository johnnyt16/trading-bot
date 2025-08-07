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
            
            if not clock.is_open:
                logger.info("Market closed, waiting...")
                await asyncio.sleep(300)  # 5 minutes
                continue
            
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