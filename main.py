#!/usr/bin/env python3
"""
Trading Bot Main Entry Point
Professional momentum trading system for Alpaca
"""

import sys
import argparse
from loguru import logger
from datetime import datetime
import time

from src.core import Config, test_connection, DatabaseManager, RiskManager, OptimalTradingSchedule
from src.strategies import EarlyDetectionIntegration, SocialIntegration, UltimateTradingStrategy
from src.utils import AlertSystem, Backtester
import alpaca_trade_api as tradeapi
import asyncio
import os

def setup_logging(log_level="INFO"):
    logger.remove()
    logger.add(sys.stderr, format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}", level=log_level)
    logger.add("logs/trading_{time:YYYY-MM-DD}.log", rotation="1 day", retention="30 days", level=log_level)

def run_backtest(symbols=None, period="3mo", initial_capital=1000):
    logger.info("Starting backtest mode...")
    
    if symbols is None:
        symbols = Config.WATCHLIST
    
    backtester = Backtester(initial_capital=initial_capital)
    stats = backtester.run_backtest(symbols)
    backtester.print_summary(stats)
    backtester.save_results(stats)
    
    return stats

def run_paper_trading():
    logger.info("Starting paper trading mode...")
    
    if not test_connection():
        logger.error("Connection test failed. Please check your API keys.")
        return
    
    db = DatabaseManager()
    risk_manager = RiskManager()
    alert_system = AlertSystem()
    
    alert_system.send_system_status("online", "Trading bot started in paper mode")
    
    # Initialize API
    api = tradeapi.REST(
        os.getenv('ALPACA_API_KEY'),
        os.getenv('ALPACA_SECRET_KEY'),
        Config.ALPACA_BASE_URL
    )
    
    # Initialize new modules
    early_detection = EarlyDetectionIntegration(api)
    social_scanner = SocialIntegration()
    ultimate_strategy = UltimateTradingStrategy()
    schedule = OptimalTradingSchedule()
    
    try:
        # Main trading loop
        asyncio.run(run_trading_loop(
            api, early_detection, social_scanner, 
            ultimate_strategy, schedule, alert_system
        ))
    except KeyboardInterrupt:
        logger.info("Trading bot stopped by user")
        alert_system.send_system_status("offline", "Trading bot stopped by user")
    except Exception as e:
        logger.error(f"Trading bot error: {e}")
        alert_system.send_error_alert(str(e))
    finally:
        db.close()

def run_live_trading():
    logger.warning("LIVE TRADING MODE - REAL MONEY AT RISK!")
    response = input("Are you sure you want to run in LIVE mode? (type 'YES' to confirm): ")
    
    if response != "YES":
        logger.info("Live trading cancelled")
        return
    
    logger.info("Starting live trading mode...")
    
    Config.ALPACA_BASE_URL = "https://api.alpaca.markets"
    
    if not test_connection():
        logger.error("Connection test failed. Please check your API keys.")
        return
    
    db = DatabaseManager()
    risk_manager = RiskManager()
    alert_system = AlertSystem()
    
    alert_system.send_system_status("online", "⚠️ LIVE TRADING STARTED - REAL MONEY ⚠️")
    
    # Initialize API
    api = tradeapi.REST(
        os.getenv('ALPACA_API_KEY'),
        os.getenv('ALPACA_SECRET_KEY'),
        Config.ALPACA_BASE_URL
    )
    
    # Initialize new modules
    early_detection = EarlyDetectionIntegration(api)
    social_scanner = SocialIntegration()
    ultimate_strategy = UltimateTradingStrategy()
    schedule = OptimalTradingSchedule()
    
    try:
        # Main trading loop
        asyncio.run(run_trading_loop(
            api, early_detection, social_scanner, 
            ultimate_strategy, schedule, alert_system
        ))
    except KeyboardInterrupt:
        logger.info("Trading bot stopped by user")
        alert_system.send_system_status("offline", "Live trading stopped by user")
    except Exception as e:
        logger.error(f"Trading bot error: {e}")
        alert_system.send_error_alert(str(e))
    finally:
        db.close()

def test_setup():
    logger.info("Running setup test...")
    
    from scripts.test_setup import test_environment
    
    if test_environment():
        logger.success("Setup test passed!")
        return True
    else:
        logger.error("Setup test failed. Please fix the issues above.")
        return False

async def run_trading_loop(api, early_detection, social_scanner, 
                           ultimate_strategy, schedule, alert_system):
    """
    Main trading loop integrating all strategies
    """
    logger.info("Starting integrated trading loop")
    
    while True:
        try:
            # Get current trading session
            current_session = schedule.get_current_session()
            scan_strategy = schedule.get_scan_strategy()
            
            logger.info(f"Current session: {current_session}")
            
            if current_session == 'market_closed':
                logger.info("Market closed, waiting...")
                await asyncio.sleep(300)  # Wait 5 minutes
                continue
            
            # Get early detection signals
            early_opportunities = await early_detection.scanner.get_priority_trades()
            
            # Process opportunities
            for opp in early_opportunities:
                # Check if we should enter
                if await early_detection.should_enter_position(opp['symbol'], opp):
                    # Enhance with social signals
                    social_data = social_scanner.enhance_signal_with_social(
                        opp['symbol'], 
                        opp.get('opportunity_score', 0)
                    )
                    
                    # Calculate position size
                    position_size = await early_detection.get_position_size(opp)
                    
                    logger.info(f"Signal for {opp['symbol']}: "
                              f"Score={social_data['final_score']}, "
                              f"Size={position_size:.2%}")
                    
                    # Here you would execute the trade
                    # For now, just log it
                    alert_system.send_trade_alert(
                        f"BUY SIGNAL: {opp['symbol']} at ${opp['current_price']:.2f}"
                    )
            
            # Wait based on scan frequency
            wait_time = scan_strategy.get('scan_frequency', 15) * 60
            await asyncio.sleep(wait_time)
            
        except Exception as e:
            logger.error(f"Error in trading loop: {e}")
            await asyncio.sleep(60)  # Wait 1 minute on error

def analyze_performance():
    logger.info("Analyzing trading performance...")
    
    db = DatabaseManager()
    metrics = db.calculate_performance_metrics()
    
    if not metrics:
        logger.warning("No trades found in database")
        return
    
    print("\n" + "="*60)
    print("PERFORMANCE ANALYSIS")
    print("="*60)
    print(f"Total Trades: {metrics.get('total_trades', 0)}")
    print(f"Winning Trades: {metrics.get('winning_trades', 0)}")
    print(f"Losing Trades: {metrics.get('losing_trades', 0)}")
    print(f"Win Rate: {metrics.get('win_rate', 0):.2%}")
    print(f"Total P&L: ${metrics.get('total_pnl', 0):.2f}")
    print(f"Average Win: ${metrics.get('avg_win', 0):.2f}")
    print(f"Average Loss: ${metrics.get('avg_loss', 0):.2f}")
    print("="*60)
    
    db.close()

def main():
    parser = argparse.ArgumentParser(description='Professional Trading Bot for Alpaca')
    parser.add_argument('mode', choices=['test', 'backtest', 'paper', 'live', 'analyze'],
                       help='Operating mode')
    parser.add_argument('--symbols', nargs='+', help='Symbols to trade (default: from config)')
    parser.add_argument('--capital', type=float, default=1000, help='Initial capital for backtest')
    parser.add_argument('--period', default='3mo', help='Backtest period (1mo, 3mo, 6mo, 1y)')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level')
    
    args = parser.parse_args()
    
    setup_logging(args.log_level)
    
    logger.info(f"Trading Bot v1.0 - Mode: {args.mode.upper()}")
    
    if args.mode == 'test':
        success = test_setup()
        sys.exit(0 if success else 1)
    
    elif args.mode == 'backtest':
        stats = run_backtest(
            symbols=args.symbols,
            period=args.period,
            initial_capital=args.capital
        )
        
        if stats.get('total_return', 0) > 0:
            logger.success(f"Backtest profitable! Return: {stats['total_return']:.2f}%")
        else:
            logger.warning(f"Backtest showed loss: {stats.get('total_return', 0):.2f}%")
    
    elif args.mode == 'paper':
        run_paper_trading()
    
    elif args.mode == 'live':
        run_live_trading()
    
    elif args.mode == 'analyze':
        analyze_performance()

if __name__ == "__main__":
    main()