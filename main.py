#!/usr/bin/env python3
"""
main.py - Simplified main file for GPT-5 autonomous trading
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
import os
import pytz
sys.path.append(str(Path(__file__).parent))

from src.ai_brain.gpt5_trading_system import GPT5TradingBrain
from src.ai_brain.overnight_researcher import OvernightResearcher
from src.core.position_manager import PositionManager
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
        position_manager = PositionManager(api=brain.alpaca)
        monitor_task = asyncio.create_task(position_manager.monitor_positions())
        
        logger.info("🚀 GPT-5 Autonomous Trading Started")
        logger.info("Target: $1,000 → $10,000")
        
        # Track if we've already executed morning trades
        morning_trades_executed = False
        
        # The main trading loop
        while True:
            # Check market status
            clock = brain.alpaca.get_clock()
            # Use Eastern timezone for consistency with market hours
            eastern = pytz.timezone('US/Eastern')
            current_time = datetime.now(pytz.utc).astimezone(eastern)
            current_hour = current_time.hour
            weekday = current_time.weekday()  # Monday=0..Sunday=6
            is_weekday = weekday < 5
            
            # Extended hours: 4 AM - 9:30 AM and 4 PM - 8 PM ET (weekdays only)
            is_premarket = is_weekday and ((current_hour >= 4 and current_hour < 9) or (current_hour == 9 and current_time.minute < 30))
            is_afterhours = is_weekday and (current_hour >= 16 and current_hour < 20)
            is_extended = is_premarket or is_afterhours
            
            if not clock.is_open and not is_extended:
                # Align timezones for subtraction and display
                next_open_dt = clock.next_open
                try:
                    # If tz-naive, assume UTC per Alpaca API
                    if next_open_dt.tzinfo is None:
                        next_open_dt = pytz.utc.localize(next_open_dt)
                except Exception:
                    pass
                next_open_et = next_open_dt.astimezone(eastern)
                next_open = next_open_et.strftime('%Y-%m-%d %H:%M:%S ET')
                hours_until_open = (next_open_dt - datetime.now(pytz.utc)).total_seconds() / 3600
                logger.info(f"Market closed. Opens in {hours_until_open:.1f} hours at {next_open}")
                
                # Weekend smart gating to avoid unnecessary calls
                weekday = current_time.weekday()  # Mon=0..Sun=6
                if weekday == 5:  # Saturday
                    logger.info("🛌 Weekend (Saturday): conserving credits; skipping overnight research")
                    await asyncio.sleep(1800)  # 30m sleep
                    continue
                if weekday == 6 and hours_until_open > 12:  # Sunday >12h from premarket
                    logger.info("🛌 Weekend (Sunday >12h to premarket): conserving credits; skipping cycles")
                    await asyncio.sleep(1800)
                    continue

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
                if current_time.minute < 10:
                    logger.info("📚 Analyzing recent performance...")
                    await brain.learn_and_adapt()
                
                # Reset morning trades flag when new day starts
                if current_time.hour == 0:
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
                            executed = await brain.execute_trade(analysis)
                            if executed:
                                position_manager.add_position(
                                    symbol=analysis['symbol'],
                                    entry_price=analysis['entry_price'],
                                    stop_loss=analysis['stop_loss'],
                                    take_profit=analysis['target_1'],
                                    strategy_type='standard'
                                )
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
                            executed = await brain.execute_trade(analysis)
                            if executed:
                                position_manager.add_position(
                                    symbol=analysis['symbol'],
                                    entry_price=analysis['entry_price'],
                                    stop_loss=analysis['stop_loss'],
                                    take_profit=analysis['target_1'],
                                    strategy_type='standard'
                                )
                            morning_trades_executed = True
                    
                    overnight_researcher.clear_watchlist()
            
            # Regular scanning for more opportunities (respect cost mode cadence)
            if is_weekday:
                logger.info("🔍 Scanning for opportunities...")
                opportunities = await brain.autonomous_market_scan()
                
                # Analyze and trade top opportunities
                for opp in opportunities[:3]:
                    analysis = await brain.deep_analysis(opp['symbol'])
                    
                    if analysis['decision'] == 'GO':
                        executed = await brain.execute_trade(analysis)
                        if executed:
                            position_manager.add_position(
                                symbol=analysis['symbol'],
                                entry_price=analysis['entry_price'],
                                stop_loss=analysis['stop_loss'],
                                take_profit=analysis['target_1'],
                                strategy_type='standard'
                            )
            
            # Position management handled by PositionManager monitor task
            
            # Learn (every hour)
            if current_time.minute == 0:
                await brain.learn_and_adapt()
            
            # Adjust loop sleep by cost mode and session
            cost_mode = os.getenv('COST_MODE', 'low').lower()
            if is_premarket or clock.is_open:
                # During active sessions, still avoid hammering
                sleep_seconds = 60 if cost_mode == 'low' else 45 if cost_mode == 'medium' else 30
            else:
                sleep_seconds = 300 if cost_mode == 'low' else 180 if cost_mode == 'medium' else 120
            await asyncio.sleep(sleep_seconds)
            
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        try:
            monitor_task.cancel()
        except Exception:
            pass
    except Exception as e:
        logger.error(f"Fatal error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down (KeyboardInterrupt). Bye!")
        sys.exit(0)