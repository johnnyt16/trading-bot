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
from src.ai_brain.overnight_researcher import OvernightResearcher
from loguru import logger

async def main():
    """
    Main function - GPT-5 runs everything autonomously
    """
    try:
        # Initialize the AI brain
        logger.info("Initializing GPT-5 Trading System...")
        brain = GPT5TradingBrain()
        overnight_researcher = OvernightResearcher(brain)
        
        logger.info("🚀 GPT-5 Autonomous Trading Started")
        logger.info("Target: $1,000 → $10,000")
        
        # Track if we've already executed morning trades
        morning_trades_executed = False
        
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
                hours_until_open = (clock.next_open - datetime.now()).total_seconds() / 3600
                logger.info(f"Market closed. Opens in {hours_until_open:.1f} hours at {next_open}")
                
                # OVERNIGHT RESEARCH MODE - Build watchlist of 6 high-confidence stocks
                logger.info("🌙 OVERNIGHT RESEARCH MODE - Building tomorrow's watchlist")
                
                # Run the overnight research cycle
                watchlist = await overnight_researcher.overnight_research_cycle()
                
                # Show current watchlist status
                if watchlist:
                    logger.info(f"📋 Current watchlist: {len(watchlist)}/{overnight_researcher.max_watchlist_size} stocks")
                    avg_confidence = sum(s.get('confidence', 0) for s in watchlist) / len(watchlist)
                    logger.info(f"   Average confidence: {avg_confidence:.1f}%")
                    
                    # Show top 3
                    for stock in watchlist[:3]:
                        logger.info(f"   • {stock['symbol']}: {stock.get('confidence')}% - {stock.get('catalyst', 'N/A')[:40]}")
                
                # Learn from recent trades every hour
                if datetime.now().minute < 10:
                    logger.info("📚 Analyzing recent performance...")
                    await brain.learn_and_adapt()
                
                # Reset morning trades flag when new day starts
                if datetime.now().hour == 0:
                    morning_trades_executed = False
                
                # Wait longer during deep overnight (less frequent checks)
                wait_minutes = 15 if hours_until_open > 6 else 10 if hours_until_open > 2 else 5
                logger.info(f"Next research cycle in {wait_minutes} minutes...")
                await asyncio.sleep(wait_minutes * 60)
                continue
            
            if is_premarket:
                logger.info("🌅 PRE-MARKET TRADING (4 AM - 9:30 AM ET)")
                logger.info("Prime time for news reactions and gap plays!")
                
                # Execute watchlist trades at pre-market open (4 AM) if we have them
                if not morning_trades_executed and current_hour == 4 and overnight_researcher.watchlist:
                    logger.info("🚀 EXECUTING OVERNIGHT WATCHLIST - Top opportunities from research")
                    top_opportunities = overnight_researcher.get_top_opportunities(3)  # Execute top 3
                    
                    for opp in top_opportunities:
                        logger.info(f"Analyzing watchlist stock: {opp['symbol']}")
                        analysis = await brain.deep_analysis(opp['symbol'])
                        
                        if analysis['decision'] == 'GO':
                            await brain.execute_trade(analysis)
                            morning_trades_executed = True
                    
                    # Clear watchlist after execution
                    overnight_researcher.clear_watchlist()
                    
            elif is_afterhours:
                logger.info("🌙 AFTER-HOURS TRADING (4 PM - 8 PM ET)")
                logger.info("Earnings reactions and news catalysts!")
            elif clock.is_open:
                logger.info("📈 Regular market hours active")
                
                # Execute watchlist at market open if not done in pre-market
                if not morning_trades_executed and current_hour == 9 and current_time.minute >= 30 and overnight_researcher.watchlist:
                    logger.info("🔔 MARKET OPEN - Executing overnight watchlist")
                    top_opportunities = overnight_researcher.get_top_opportunities(3)
                    
                    for opp in top_opportunities:
                        analysis = await brain.deep_analysis(opp['symbol'])
                        if analysis['decision'] == 'GO':
                            await brain.execute_trade(analysis)
                            morning_trades_executed = True
                    
                    overnight_researcher.clear_watchlist()
            
            # Regular scanning for more opportunities
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