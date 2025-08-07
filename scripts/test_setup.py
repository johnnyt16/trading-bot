#!/usr/bin/env python3

import sys
import os
import asyncio

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core import Config, test_connection
from src.strategies import EarlyDetectionIntegration, SocialIntegration, UltimateTradingStrategy
import alpaca_trade_api as tradeapi


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

    # Test 3: Initialize API
    print("\n3. Testing API initialization...")
    try:
        api = tradeapi.REST(
            Config.ALPACA_API_KEY,
            Config.ALPACA_SECRET_KEY,
            Config.ALPACA_BASE_URL
        )
        print("   ✅ API initialized successfully")
        tests_passed.append(True)
    except Exception as e:
        print(f"   ❌ API initialization failed: {e}")
        tests_passed.append(False)
        return False

    # Test 4: Early Detection Scanner
    print("\n4. Testing Early Detection Scanner...")
    try:
        early_detection = EarlyDetectionIntegration(api)
        print("   ✅ Early Detection Scanner initialized")
        tests_passed.append(True)
    except Exception as e:
        print(f"   ❌ Early Detection Scanner failed: {e}")
        tests_passed.append(False)

    # Test 5: Social Sentiment Scanner
    print("\n5. Testing Social Sentiment Scanner...")
    try:
        social_scanner = SocialIntegration()
        print("   ✅ Social Sentiment Scanner initialized")
        tests_passed.append(True)
    except Exception as e:
        print(f"   ❌ Social Sentiment Scanner failed: {e}")
        tests_passed.append(False)

    # Test 6: Ultimate Strategy
    print("\n6. Testing Ultimate Trading Strategy...")
    try:
        ultimate_strategy = UltimateTradingStrategy()
        print("   ✅ Ultimate Trading Strategy initialized")
        tests_passed.append(True)
    except Exception as e:
        print(f"   ❌ Ultimate Trading Strategy failed: {e}")
        tests_passed.append(False)

    # Test 7: Market data access
    print("\n7. Testing market data access...")
    try:
        # Get a snapshot for a test symbol
        snapshot = api.get_snapshot("AAPL")
        if snapshot:
            print(f"   ✅ Market data working (AAPL price: ${snapshot.latest_trade.p:.2f})")
            tests_passed.append(True)
        else:
            print("   ⚠️  Market data returned empty (market may be closed)")
            tests_passed.append(True)  # Not a failure if market is closed
    except Exception as e:
        print(f"   ❌ Market data failed: {e}")
        tests_passed.append(False)

    # Test 8: Async functionality
    print("\n8. Testing async scanner functionality...")
    try:
        async def test_scanner():
            session, _ = early_detection.scanner.get_market_session()
            return session
        
        session = asyncio.run(test_scanner())
        print(f"   ✅ Async operations working (Current session: {session})")
        tests_passed.append(True)
    except Exception as e:
        print(f"   ❌ Async operations failed: {e}")
        tests_passed.append(False)

    print("\n" + "=" * 50)
    if all(tests_passed):
        print("✅ ALL TESTS PASSED!")
        print("Your bot is ready to run.")
    else:
        failed = tests_passed.count(False)
        print(f"⚠️  {failed} test(s) failed")
        print("Please fix the issues above before running the bot.")
    print("=" * 50)

    return all(tests_passed)


if __name__ == "__main__":
    success = test_environment()
    sys.exit(0 if success else 1)