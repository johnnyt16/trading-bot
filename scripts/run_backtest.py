#!/usr/bin/env python3
"""
Quick backtest runner script
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils import Backtester
from src.core import Config

def main():
    print("Running backtest with default settings...")
    
    backtester = Backtester(initial_capital=1000)
    
    symbols = ['TSLA', 'NVDA', 'AMD', 'AAPL', 'SPY']
    
    stats = backtester.run_backtest(symbols)
    
    backtester.print_summary(stats)
    
    backtester.save_results(stats)
    
    if stats.get('total_return', 0) > 0:
        print(f"\n✅ Strategy would be profitable! Return: {stats['total_return']:.2f}%")
    else:
        print(f"\n❌ Strategy would lose money. Return: {stats.get('total_return', 0):.2f}%")

if __name__ == "__main__":
    main()