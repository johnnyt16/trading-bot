#!/usr/bin/env python3
"""
Test all API connections for the GPT-5 Trading System
"""

import os
import sys
import asyncio
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

# Test imports
print("Testing imports...")
try:
    from openai import AsyncOpenAI
    print("✅ OpenAI imported")
except Exception as e:
    print(f"❌ OpenAI import failed: {e}")

try:
    from tavily import TavilyClient
    print("✅ Tavily imported")
except Exception as e:
    print(f"❌ Tavily import failed: {e}")

try:
    import alpaca_trade_api as tradeapi
    print("✅ Alpaca imported")
except Exception as e:
    print(f"❌ Alpaca import failed: {e}")

print("\n" + "="*50)

async def test_openai():
    """Test OpenAI API connection"""
    print("\n🤖 Testing OpenAI API...")
    try:
        client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Say 'Connection successful!' in 3 words"}],
            max_tokens=10
        )
        result = response.choices[0].message.content
        print(f"✅ OpenAI connected! Response: {result}")
        return True
    except Exception as e:
        print(f"❌ OpenAI connection failed: {e}")
        return False

def test_tavily():
    """Test Tavily web search"""
    print("\n🔍 Testing Tavily Web Search...")
    try:
        client = TavilyClient(api_key=os.getenv('TAVILY_API_KEY'))
        result = client.search("NVDA stock price today", max_results=1)
        if result and 'results' in result:
            print(f"✅ Tavily connected! Found {len(result['results'])} results")
            return True
        else:
            print("❌ Tavily returned no results")
            return False
    except Exception as e:
        print(f"❌ Tavily connection failed: {e}")
        return False

def test_alpaca():
    """Test Alpaca API connection"""
    print("\n📈 Testing Alpaca API...")
    try:
        api = tradeapi.REST(
            os.getenv('ALPACA_API_KEY'),
            os.getenv('ALPACA_SECRET_KEY'),
            os.getenv('ALPACA_BASE_URL')
        )
        
        # Test account access
        account = api.get_account()
        print(f"✅ Alpaca connected!")
        print(f"   Account Status: {account.status}")
        print(f"   Buying Power: ${float(account.buying_power):,.2f}")
        print(f"   Cash: ${float(account.cash):,.2f}")
        
        # Test market status
        clock = api.get_clock()
        print(f"   Market is: {'OPEN 🟢' if clock.is_open else 'CLOSED 🔴'}")
        
        return True
    except Exception as e:
        print(f"❌ Alpaca connection failed: {e}")
        return False

async def test_full_system():
    """Test full system initialization"""
    print("\n🚀 Testing Full System Initialization...")
    try:
        from src.ai_brain.gpt5_trading_system import GPT5TradingBrain
        brain = GPT5TradingBrain()
        print("✅ GPT-5 Trading Brain initialized successfully!")
        
        # Test a simple method if available
        account = brain.alpaca.get_account()
        print(f"   System ready with ${float(account.buying_power):,.2f} buying power")
        
        return True
    except Exception as e:
        print(f"❌ System initialization failed: {e}")
        print(f"   Error details: {str(e)}")
        return False

async def main():
    """Run all tests"""
    print("🎯 GPT-5 Trading System - Connection Test")
    print("="*50)
    
    results = {
        "OpenAI": await test_openai(),
        "Tavily": test_tavily(),
        "Alpaca": test_alpaca(),
        "System": await test_full_system()
    }
    
    print("\n" + "="*50)
    print("📊 Test Results Summary:")
    print("="*50)
    
    all_passed = True
    for service, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{service:15} {status}")
        if not passed:
            all_passed = False
    
    print("="*50)
    if all_passed:
        print("🎉 All systems operational! Ready to trade!")
    else:
        print("⚠️  Some connections failed. Please check your API keys.")
    
    return all_passed

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)