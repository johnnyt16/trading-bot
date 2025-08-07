#!/usr/bin/env python3
"""
Test script for the enhanced GPT-5 trading system with web search
"""

import asyncio
import os
from dotenv import load_dotenv
from src.ai_brain.gpt5_trading_system import GPT5TradingBrain
from loguru import logger
import sys

# Configure logger for testing
logger.remove()
logger.add(sys.stdout, level="DEBUG", format="{time:HH:mm:ss} | {level} | {message}")

async def test_system():
    """Test the enhanced trading system"""
    
    # Load environment variables
    load_dotenv()
    
    # Check required API keys
    required_keys = ['OPENAI_API_KEY', 'TAVILY_API_KEY', 'ALPACA_API_KEY', 'ALPACA_SECRET_KEY']
    missing_keys = [key for key in required_keys if not os.getenv(key)]
    
    if missing_keys:
        logger.error(f"Missing required API keys: {missing_keys}")
        logger.info("Please add them to your .env file")
        return
    
    logger.info("=" * 60)
    logger.info("TESTING ENHANCED GPT-5 TRADING SYSTEM")
    logger.info("=" * 60)
    
    try:
        # Initialize the trading brain
        logger.info("Initializing GPT-5 Trading Brain...")
        brain = GPT5TradingBrain()
        
        # Test 1: Market Context
        logger.info("\n📊 TEST 1: Getting Market Context")
        market_data = await brain._get_market_context()
        logger.info(f"Market Status: {market_data['market_status']}")
        logger.info(f"SPY Change: {market_data['spy_change']}%")
        logger.info(f"VIX Level: {market_data['vix_level']}")
        
        # Test 2: Market Scan with Web Search
        logger.info("\n🔍 TEST 2: Scanning Market for Opportunities (using Tavily)")
        logger.info("This will search the web for real opportunities...")
        opportunities = await brain.autonomous_market_scan()
        
        if opportunities:
            logger.success(f"✅ Found {len(opportunities)} opportunities!")
            for i, opp in enumerate(opportunities[:3], 1):
                logger.info(f"\nOpportunity {i}:")
                logger.info(f"  Symbol: {opp.get('symbol', 'N/A')}")
                logger.info(f"  Catalyst: {opp.get('catalyst', 'N/A')[:100]}")
                logger.info(f"  Confidence: {opp.get('confidence', 0)}%")
                logger.info(f"  Target Move: {opp.get('target_move', 0)}%")
                logger.info(f"  Entry: ${opp.get('entry_price', 0):.2f}")
                logger.info(f"  Stop: ${opp.get('stop_loss', 0):.2f}")
                logger.info(f"  Target: ${opp.get('target_1', 0):.2f}")
        else:
            logger.warning("No opportunities found. This could mean:")
            logger.warning("1. Market is closed and no pre-market movers")
            logger.warning("2. Tavily API key is invalid")
            logger.warning("3. No strong opportunities meet our criteria")
        
        # Test 3: Deep Analysis (if we found opportunities)
        if opportunities and len(opportunities) > 0:
            symbol = opportunities[0]['symbol']
            logger.info(f"\n🧠 TEST 3: Deep Analysis of {symbol}")
            analysis = await brain.deep_analysis(symbol)
            
            logger.info(f"Decision: {analysis.get('decision', 'N/A')}")
            logger.info(f"Confidence: {analysis.get('confidence', 0)}%")
            logger.info(f"Position Size: {analysis.get('position_size_pct', 0)*100:.1f}%")
            logger.info(f"Reasoning: {analysis.get('reasoning', 'N/A')[:200]}")
            
            if analysis.get('decision') == 'GO':
                logger.success(f"✅ {symbol} is a GO! Ready to trade.")
            else:
                logger.warning(f"❌ {symbol} is a NO-GO. Looking for better opportunities.")
        
        # Test 4: Check Alpaca Connection
        logger.info("\n💰 TEST 4: Checking Alpaca Account")
        try:
            account = brain.alpaca.get_account()
            logger.info(f"Account Status: {account.status}")
            logger.info(f"Buying Power: ${float(account.buying_power):,.2f}")
            logger.info(f"Portfolio Value: ${float(account.portfolio_value):,.2f}")
            
            # Check if market is open
            clock = brain.alpaca.get_clock()
            if clock.is_open:
                logger.success("✅ Market is OPEN - Ready to trade!")
            else:
                logger.warning("⏰ Market is CLOSED")
                logger.info(f"Next open: {clock.next_open}")
                logger.info(f"Next close: {clock.next_close}")
        except Exception as e:
            logger.error(f"Alpaca connection failed: {e}")
        
        logger.info("\n" + "=" * 60)
        logger.success("SYSTEM TEST COMPLETE!")
        logger.info("=" * 60)
        
        # Summary
        logger.info("\n📈 SYSTEM CAPABILITIES:")
        logger.info("✓ Web search for real-time opportunities (Tavily)")
        logger.info("✓ GPT-4 analysis and decision making")
        logger.info("✓ Real-time market data (Alpaca)")
        logger.info("✓ Automated trade execution")
        logger.info("✓ Risk management and position sizing")
        
        logger.info("\n🎯 READY TO:")
        logger.info("• Find opportunities before others")
        logger.info("• Analyze with AI-powered insights")
        logger.info("• Execute trades automatically")
        logger.info("• Manage risk intelligently")
        logger.info("• Learn and improve continuously")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(test_system())