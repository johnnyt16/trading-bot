#!/usr/bin/env python3
"""Debug Alpaca connection issue"""

import os
from dotenv import load_dotenv
import alpaca_trade_api as tradeapi

# Load environment variables
load_dotenv()

# Get credentials
api_key = os.getenv('ALPACA_API_KEY')
secret_key = os.getenv('ALPACA_SECRET_KEY')

print("API Key:", api_key[:10] + "..." if api_key else "None")
print("Secret Key:", secret_key[:10] + "..." if secret_key else "None")

# Try different base URLs
base_urls = [
    "https://paper-api.alpaca.markets",
    "https://paper-api.alpaca.markets/",
    "https://api.alpaca.markets",
]

for base_url in base_urls:
    print(f"\nTrying base URL: {base_url}")
    try:
        api = tradeapi.REST(
            key_id=api_key,
            secret_key=secret_key,
            base_url=base_url,
            api_version='v2'
        )
        
        account = api.get_account()
        print(f"✅ SUCCESS! Connected to Alpaca")
        print(f"   Account Status: {account.status}")
        print(f"   Buying Power: ${account.buying_power}")
        print(f"   Portfolio Value: ${account.portfolio_value}")
        break
        
    except Exception as e:
        print(f"❌ Failed: {e}")

print("\nNow trying without api_version parameter:")
try:
    api = tradeapi.REST(
        api_key,
        secret_key,
        "https://paper-api.alpaca.markets"
    )
    
    account = api.get_account()
    print(f"✅ SUCCESS without api_version!")
    print(f"   Portfolio Value: ${account.portfolio_value}")
    
except Exception as e:
    print(f"❌ Failed: {e}")