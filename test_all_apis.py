#!/usr/bin/env python3
"""
Test ALL external APIs and components to ensure everything works
"""

import asyncio
import os
from dotenv import load_dotenv
import alpaca_trade_api as tradeapi
from src.strategies.social_sentiment_scanner import SocialSentimentScanner
from src.strategies.early_detection_scanner import OptimizedEarlyDetectionScanner
from src.core.optimal_schedule import OptimalTradingSchedule

load_dotenv()

def test_stocktwits():
    """Test StockTwits API (no key required)"""
    print("\n🔍 Testing StockTwits API...")
    try:
        scanner = SocialSentimentScanner()
        result = scanner.get_stocktwits_sentiment('TSLA')
        
        if result and 'sentiment_score' in result:
            print(f"✅ StockTwits working!")
            print(f"   TSLA sentiment: {result.get('sentiment_score', 0):.2f}")
            print(f"   Message volume: {result.get('message_volume', 0)}")
            print(f"   Bullish %: {result.get('bullish_pct', 0):.1f}%")
            return True
        else:
            print("⚠️ StockTwits returned empty data (might be rate limited)")
            return False
    except Exception as e:
        print(f"❌ StockTwits error: {e}")
        return False

def test_reddit_wsb():
    """Test Reddit WSB scraping (no key required)"""
    print("\n🔍 Testing Reddit WSB scraping...")
    try:
        scanner = SocialSentimentScanner()
        result = scanner.scan_wsb_daily_thread()
        
        if result:
            print(f"✅ Reddit WSB working!")
            print(f"   Found {len(result)} tickers mentioned")
            for ticker, data in list(result.items())[:3]:
                print(f"   {ticker}: {data['mentions']} mentions")
            return True
        else:
            print("⚠️ Reddit returned no data (daily thread might not be available)")
            return False
    except Exception as e:
        print(f"❌ Reddit error: {e}")
        return False

def test_alpaca_news():
    """Test Alpaca news API"""
    print("\n🔍 Testing Alpaca News API...")
    try:
        api = tradeapi.REST(
            os.getenv('ALPACA_API_KEY'),
            os.getenv('ALPACA_SECRET_KEY'),
            os.getenv('ALPACA_BASE_URL')
        )
        
        news = api.get_news(symbol='AAPL', limit=3)
        
        if news:
            print(f"✅ Alpaca News API working!")
            print(f"   Found {len(news)} news items for AAPL")
            for article in news[:2]:
                print(f"   - {article.headline[:60]}...")
            return True
        else:
            print("⚠️ No news found (might be after hours)")
            return False
    except Exception as e:
        print(f"❌ Alpaca News error: {e}")
        return False

async def test_early_detection():
    """Test early detection scanner with real data"""
    print("\n🔍 Testing Early Detection Scanner...")
    try:
        api = tradeapi.REST(
            os.getenv('ALPACA_API_KEY'),
            os.getenv('ALPACA_SECRET_KEY'),
            os.getenv('ALPACA_BASE_URL')
        )
        
        scanner = OptimizedEarlyDetectionScanner(api)
        
        # Get market session
        session, minutes = scanner.get_market_session()
        print(f"   Current session: {session}")
        
        # Try to get some market data
        snapshot = api.get_snapshot('TSLA')
        if snapshot and snapshot.minute_bar:
            current = snapshot.minute_bar.c
            prev = snapshot.prev_daily_bar.c if snapshot.prev_daily_bar else 0
            if prev > 0:
                change = (current - prev) / prev * 100
                print(f"✅ Market data working!")
                print(f"   TSLA current: ${current:.2f}")
                print(f"   TSLA change: {change:.2f}%")
                
                # Test move detection logic
                if 0.5 <= abs(change) <= 3:
                    print(f"   ⚡ TSLA is in early detection range!")
                elif abs(change) > 3:
                    print(f"   📈 TSLA move too extended for early entry")
                else:
                    print(f"   😴 TSLA not moving much")
                return True
        else:
            print("⚠️ Market data not available (market closed)")
            return True  # Not a failure, just closed
            
    except Exception as e:
        print(f"❌ Early detection error: {e}")
        return False

def test_market_schedule():
    """Test market schedule detection"""
    print("\n🔍 Testing Market Schedule...")
    try:
        schedule = OptimalTradingSchedule()
        session = schedule.get_current_session()
        strategy = schedule.get_scan_strategy()
        
        print(f"✅ Schedule working!")
        print(f"   Current session: {session}")
        print(f"   Scan frequency: {strategy.get('scan_frequency', 'N/A')} minutes")
        print(f"   Focus areas: {', '.join(strategy.get('focus', []))}")
        return True
    except Exception as e:
        print(f"❌ Schedule error: {e}")
        return False

def test_combined_social_score():
    """Test combined social sentiment scoring"""
    print("\n🔍 Testing Combined Social Sentiment...")
    try:
        scanner = SocialSentimentScanner()
        
        # Test with a popular ticker
        score = scanner.get_social_score('NVDA')
        
        print(f"✅ Combined social scoring working!")
        print(f"   NVDA social score: {score['social_score']}/100")
        print(f"   Action: {score['action']}")
        if score['signals']:
            print(f"   Signals: {', '.join(score['signals'][:2])}")
        return True
    except Exception as e:
        print(f"❌ Combined social error: {e}")
        return False

async def main():
    print("="*60)
    print("🧪 TESTING ALL TRADING BOT APIS & COMPONENTS")
    print("="*60)
    
    results = []
    
    # Test each component
    results.append(("StockTwits API", test_stocktwits()))
    results.append(("Reddit WSB Scraping", test_reddit_wsb()))
    results.append(("Alpaca News API", test_alpaca_news()))
    results.append(("Early Detection Scanner", await test_early_detection()))
    results.append(("Market Schedule", test_market_schedule()))
    results.append(("Combined Social Sentiment", test_combined_social_score()))
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    working = 0
    for name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {name}")
        if result:
            working += 1
    
    print(f"\nTotal: {working}/{len(results)} components working")
    
    if working == len(results):
        print("\n🎉 ALL SYSTEMS OPERATIONAL!")
        print("Your bot is ready to detect early moves and trade!")
    else:
        print("\n⚠️ Some components had issues.")
        print("Note: Some APIs may be rate limited or unavailable after hours.")
        print("The core trading functionality should still work.")

if __name__ == "__main__":
    asyncio.run(main())