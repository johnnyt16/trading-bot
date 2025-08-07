#!/usr/bin/env python3
"""
social_sentiment_scanner.py - Add to your bot for social signals
Catches retail momentum before mainstream news
"""

import requests
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import Counter
from loguru import logger

# Optional Reddit API - not required for basic functionality
try:
    import praw
    PRAW_AVAILABLE = True
except ImportError:
    PRAW_AVAILABLE = False

class SocialSentimentScanner:
    """
    Scan Reddit and StockTwits for trending stocks and sentiment
    """
    
    def __init__(self):
        # StockTwits doesn't require auth for basic calls
        self.stocktwits_base = "https://api.stocktwits.com/api/2"
        
        # Reddit - you can use without auth for read-only
        self.wsb_url = "https://www.reddit.com/r/wallstreetbets"
        
        # Track trending tickers
        self.trending_tickers = {}
        
    def get_stocktwits_sentiment(self, symbol: str) -> Dict:
        """
        Get StockTwits sentiment for a symbol
        NO API KEY REQUIRED!
        """
        try:
            # Free API endpoint
            url = f"{self.stocktwits_base}/streams/symbol/{symbol}.json"
            response = requests.get(url)
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract sentiment from messages
                messages = data.get('messages', [])
                
                if not messages:
                    return {'sentiment': 'neutral', 'volume': 0}
                
                # Count bullish vs bearish
                bullish = 0
                bearish = 0
                total = len(messages)
                
                for msg in messages:
                    if msg.get('entities', {}).get('sentiment'):
                        sentiment = msg['entities']['sentiment']['basic']
                        if sentiment == 'Bullish':
                            bullish += 1
                        elif sentiment == 'Bearish':
                            bearish += 1
                
                # Calculate sentiment score
                if bullish + bearish > 0:
                    sentiment_score = bullish / (bullish + bearish)
                else:
                    sentiment_score = 0.5  # Neutral
                
                # Check message velocity (how fast messages coming in)
                first_msg_time = datetime.strptime(
                    messages[-1]['created_at'], 
                    '%Y-%m-%dT%H:%M:%SZ'
                )
                last_msg_time = datetime.strptime(
                    messages[0]['created_at'],
                    '%Y-%m-%dT%H:%M:%SZ'
                )
                time_span = (last_msg_time - first_msg_time).seconds / 3600  # hours
                
                if time_span > 0:
                    msg_per_hour = total / time_span
                else:
                    msg_per_hour = total
                
                return {
                    'sentiment_score': sentiment_score,
                    'bullish_pct': (bullish / total * 100) if total > 0 else 0,
                    'bearish_pct': (bearish / total * 100) if total > 0 else 0,
                    'message_volume': total,
                    'messages_per_hour': msg_per_hour,
                    'is_trending': msg_per_hour > 20,  # 20+ messages/hour = trending
                    'signal': self._interpret_sentiment(sentiment_score, msg_per_hour)
                }
            
        except Exception as e:
            logger.error(f"Error getting StockTwits for {symbol}: {e}")
        
        return {'sentiment': 'neutral', 'volume': 0}
    
    def scan_wsb_daily_thread(self) -> Dict[str, int]:
        """
        Scan WallStreetBets daily thread for trending tickers
        NO API KEY REQUIRED - just scraping
        """
        trending = Counter()
        
        try:
            # Get daily thread without auth
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            
            # WSB Daily Discussion thread
            url = f"{self.wsb_url}/hot.json"
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                
                # Find daily discussion thread
                for post in data['data']['children']:
                    title = post['data']['title']
                    if 'Daily Discussion' in title or 'What Are Your Moves' in title:
                        # Get thread comments
                        thread_id = post['data']['id']
                        comments_url = f"{self.wsb_url}/comments/{thread_id}.json"
                        
                        comments_response = requests.get(comments_url, headers=headers)
                        if comments_response.status_code == 200:
                            comments_data = comments_response.json()
                            
                            # Extract tickers from comments
                            tickers = self._extract_tickers_from_comments(comments_data)
                            trending.update(tickers)
                        break
                
                # Get top trending
                top_trending = dict(trending.most_common(20))
                
                # Add signal strength
                result = {}
                for ticker, count in top_trending.items():
                    result[ticker] = {
                        'mentions': count,
                        'signal': self._interpret_wsb_mentions(count)
                    }
                
                return result
            
        except Exception as e:
            logger.error(f"Error scanning WSB: {e}")
        
        return {}
    
    def _extract_tickers_from_comments(self, comments_data) -> List[str]:
        """
        Extract stock tickers from Reddit comments
        """
        tickers = []
        
        # Common stock pattern: 1-5 uppercase letters
        ticker_pattern = r'\b[A-Z]{1,5}\b'
        
        # Common words to exclude (not tickers)
        exclude = {'I', 'A', 'DD', 'WSB', 'YOLO', 'LOL', 'ETF', 'IPO', 
                  'CEO', 'FBI', 'USD', 'IMO', 'ATH', 'PM', 'AM', 'EDIT',
                  'TLDR', 'EPS', 'PE', 'TA', 'FA', 'SEC', 'NYSE', 'FDA'}
        
        def extract_from_comment(comment):
            try:
                body = comment['data'].get('body', '')
                
                # Find potential tickers
                matches = re.findall(ticker_pattern, body)
                
                for match in matches:
                    if match not in exclude and len(match) >= 2:
                        # Additional check: if preceded by $, definitely a ticker
                        if f'${match}' in body:
                            tickers.append(match)
                        # Or if it appears multiple times
                        elif body.count(match) >= 2:
                            tickers.append(match)
                
                # Recursively check replies
                if 'replies' in comment['data'] and comment['data']['replies']:
                    for reply in comment['data']['replies']['data']['children']:
                        extract_from_comment(reply)
                        
            except:
                pass
        
        # Process all comments
        if len(comments_data) > 1:
            for comment in comments_data[1]['data']['children']:
                extract_from_comment(comment)
        
        return tickers
    
    def _interpret_sentiment(self, sentiment_score: float, msg_volume: float) -> str:
        """
        Interpret StockTwits sentiment into trading signal
        """
        if sentiment_score > 0.8 and msg_volume > 30:
            return "STRONG_BUY"
        elif sentiment_score > 0.65 and msg_volume > 20:
            return "BUY"
        elif sentiment_score < 0.35 and msg_volume > 20:
            return "SELL"
        elif msg_volume > 50:
            return "HIGH_ATTENTION"
        else:
            return "NEUTRAL"
    
    def _interpret_wsb_mentions(self, mention_count: int) -> str:
        """
        Interpret WSB mention count into signal
        """
        if mention_count > 100:
            return "WSB_FRENZY"  # Meme stock alert
        elif mention_count > 50:
            return "WSB_TRENDING"
        elif mention_count > 20:
            return "WSB_MENTIONED"
        else:
            return "LOW_BUZZ"
    
    def get_social_score(self, symbol: str) -> Dict:
        """
        Combined social sentiment score for a symbol
        """
        # Get StockTwits sentiment
        st_data = self.get_stocktwits_sentiment(symbol)
        
        # Check WSB mentions
        wsb_data = self.scan_wsb_daily_thread()
        wsb_mentions = wsb_data.get(symbol, {}).get('mentions', 0)
        
        # Calculate combined score
        social_score = 0
        signals = []
        
        # StockTwits scoring
        if st_data.get('sentiment_score', 0.5) > 0.7:
            social_score += 30
            signals.append(f"StockTwits {st_data['bullish_pct']:.0f}% bullish")
        
        if st_data.get('is_trending'):
            social_score += 20
            signals.append(f"{st_data['messages_per_hour']:.0f} msgs/hour")
        
        # Reddit scoring
        if wsb_mentions > 50:
            social_score += 30
            signals.append(f"WSB {wsb_mentions} mentions")
        elif wsb_mentions > 20:
            social_score += 15
            signals.append(f"WSB buzz")
        
        # Determine action
        if social_score >= 60:
            action = "BUY_SOCIAL_MOMENTUM"
        elif social_score >= 40:
            action = "WATCH_BUILDING"
        else:
            action = "NO_SOCIAL_SIGNAL"
        
        return {
            'symbol': symbol,
            'social_score': social_score,
            'stocktwits_sentiment': st_data.get('sentiment_score', 0.5),
            'stocktwits_volume': st_data.get('message_volume', 0),
            'wsb_mentions': wsb_mentions,
            'action': action,
            'signals': signals
        }
    
    def scan_trending_social(self) -> List[Dict]:
        """
        Find the hottest social momentum plays right now
        """
        all_trending = []
        
        # Get WSB trending
        wsb_trending = self.scan_wsb_daily_thread()
        
        # Check sentiment for top WSB stocks
        for ticker, data in list(wsb_trending.items())[:10]:
            if data['mentions'] > 20:
                # Get full social score
                score = self.get_social_score(ticker)
                if score['social_score'] >= 40:
                    all_trending.append(score)
        
        # Sort by score
        all_trending.sort(key=lambda x: x['social_score'], reverse=True)
        
        logger.info(f"Found {len(all_trending)} social momentum plays")
        
        return all_trending


# Easy integration with your bot
class SocialIntegration:
    """
    Add this to your existing scanner
    """
    
    def __init__(self):
        self.social_scanner = SocialSentimentScanner()
    
    def enhance_signal_with_social(self, symbol: str, existing_score: float) -> Dict:
        """
        Add social sentiment to existing signals
        """
        # Get social data
        social = self.social_scanner.get_social_score(symbol)
        
        # Boost existing score if social is hot
        enhanced_score = existing_score
        
        if social['action'] == 'BUY_SOCIAL_MOMENTUM':
            enhanced_score += 25
            
        elif social['action'] == 'WATCH_BUILDING':
            enhanced_score += 10
        
        return {
            'original_score': existing_score,
            'social_boost': enhanced_score - existing_score,
            'final_score': enhanced_score,
            'social_data': social
        }


# Quick test
if __name__ == "__main__":
    scanner = SocialSentimentScanner()
    
    print("\n🔥 SOCIAL SENTIMENT SCANNER TEST 🔥\n")
    
    # Test some popular tickers
    test_symbols = ['TSLA', 'GME', 'NVDA', 'SPY']
    
    for symbol in test_symbols:
        print(f"\n{symbol} Social Sentiment:")
        print("-" * 40)
        
        # Get StockTwits
        st_data = scanner.get_stocktwits_sentiment(symbol)
        print(f"StockTwits:")
        print(f"  Sentiment: {st_data.get('bullish_pct', 0):.1f}% bullish")
        print(f"  Volume: {st_data.get('message_volume', 0)} messages")
        print(f"  Trending: {st_data.get('is_trending', False)}")
        
        # Get combined score
        score = scanner.get_social_score(symbol)
        print(f"\nCombined Social Score: {score['social_score']}/100")
        print(f"Action: {score['action']}")
        if score['signals']:
            print(f"Signals: {', '.join(score['signals'])}")
    
    # Get trending from WSB
    print("\n\n🚀 WSB TRENDING STOCKS 🚀")
    print("-" * 40)
    wsb = scanner.scan_wsb_daily_thread()
    
    for ticker, data in list(wsb.items())[:5]:
        print(f"{ticker}: {data['mentions']} mentions ({data['signal']})")
    
    print("\n✅ No API keys required for any of this!")