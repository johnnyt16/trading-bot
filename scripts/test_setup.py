#!/usr/bin/env python3

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core import Config, test_connection
from src.strategies import MomentumTradingBot


def test_environment():
    print("=" * 50)
    print("TRADING BOT SETUP TEST")
    print("=" * 50)

    tests_passed = []

    # Test 1: Check environment variables
    print("\n1. Checking environment variables...")
    if Config.ALPACA_API_KEY == "your_api_key_here" or not Config.ALPACA_API_KEY:
        print("   ❌ API keys not configured")
        print("   Please edit .env file and add your Alpaca API keys")
        tests_passed.append(False)
    else:
        print("   ✅ API keys found")
        tests_passed.append(True)

    # Test 2: Alpaca connection
    print("\n2. Testing Alpaca connection...")
    if not test_connection():
        print("   ❌ Connection failed")
        print("   Check your API keys and network connection")
        tests_passed.append(False)
    else:
        print("   ✅ Connected to Alpaca successfully")
        tests_passed.append(True)

    # Test 3: Bot initialization
    print("\n3. Testing bot initialization...")
    try:
        bot = MomentumTradingBot()
        print("   ✅ Bot initialized successfully")
        tests_passed.append(True)

        # Test 4: Market data
        print("\n4. Testing market data access...")
        score = bot.calculate_momentum_score("AAPL")
        if score is not None:
            print(f"   ✅ Market data working (AAPL score: {score:.2f})")
            tests_passed.append(True)
        else:
            print("   ⚠️  Market data returned no score")
            tests_passed.append(False)

    except Exception as e:
        print(f"   ❌ Bot initialization failed: {e}")
        tests_passed.append(False)

    # Summary
    print("\n" + "=" * 50)
    if all(tests_passed):
        print("✅ ALL TESTS PASSED!")
        print("=" * 50)
        print("\nNext steps:")
        print("1. Run backtest: python main.py backtest")
        print("2. Start paper trading: python main.py paper")
        print("3. Check performance: python main.py analyze")
        return True
    else:
        failed_count = len([t for t in tests_passed if not t])
        print(f"❌ {failed_count} TEST(S) FAILED")
        print("=" * 50)
        print("\nPlease fix the issues above and try again.")
        return False


if __name__ == "__main__":
    success = test_environment()
    sys.exit(0 if success else 1)