#!/usr/bin/env python3
"""Simple test to verify Alpaca connection works"""

import os
from dotenv import load_dotenv
import alpaca_trade_api as tradeapi

# Load environment variables
load_dotenv()

# Get credentials directly
api_key = os.getenv('ALPACA_API_KEY')
secret_key = os.getenv('ALPACA_SECRET_KEY')
base_url = os.getenv('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets')

print("Testing Alpaca Connection...")
print("="*50)

try:
    # Create API client
    api = tradeapi.REST(api_key, secret_key, base_url)
    
    # Get account
    account = api.get_account()
    
    print("✅ Connected to Alpaca!")
    print(f"   Account Status: {account.status}")
    print(f"   Portfolio Value: ${account.portfolio_value}")
    print(f"   Buying Power: ${account.buying_power}")
    print(f"   Cash: ${account.cash}")
    
    # Test market data
    spy = api.get_latest_trade("SPY")
    print(f"\n✅ Market Data Working!")
    print(f"   SPY Price: ${spy.price:.2f}")
    
    # Test clock
    clock = api.get_clock()
    print(f"\n✅ Market Clock Working!")
    print(f"   Market is: {'OPEN' if clock.is_open else 'CLOSED'}")
    
    print("="*50)
    print("✅ All tests passed! Your bot is ready to trade!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import sys
    sys.exit(1)