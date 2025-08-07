#!/usr/bin/env python3
"""
early_detection_scanner.py - OPTIMIZED VERSION
Catches moves TRULY early with proper timing considerations
Incorporates 4AM-9:30AM pre-market focus
"""

import os
import asyncio
import aiohttp
from datetime import datetime, timedelta, time
from typing import List, Dict, Optional, Tuple
import pandas as pd
import numpy as np
import alpaca_trade_api as tradeapi
from loguru import logger
import yfinance as yf
from bs4 import BeautifulSoup
import requests
import json
import pytz
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()

class OptimizedEarlyDetectionScanner:
    """
    TRULY early detection - catches moves at 0.5-3% instead of 2-5%
    Focuses on pre-market and opening 30 minutes
    """
    
    def __init__(self, api: tradeapi.REST):
        self.api = api
        self.eastern = pytz.timezone('US/Eastern')
        
        # UPDATED: Earlier detection thresholds
        self.early_thresholds = {
            'pre_market': {
                'min_move': 0.005,     # 0.5% in pre-market is significant
                'max_move': 0.03,      # 3% max - still very early
                'volume_threshold': 1.2 # Even 1.2x volume matters pre-market
            },
            'market_hours': {
                'min_move': 0.01,      # 1% minimum during market
                'max_move': 0.04,      # 4% max - not chasing
                'volume_threshold': 1.5 # 1.5x volume minimum
            },
            'opening_surge': {
                'min_move': 0.005,     # 0.5% in first 5 mins
                'max_move': 0.02,      # 2% max in first 5 mins
                'volume_threshold': 2.0 # 2x volume for opening
            }
        }
        
        # Track when moves started (critical for early detection)
        self.move_start_times = {}
        self.first_detection = {}
        
        logger.info("Optimized Early Detection Scanner initialized")
    
    def get_market_session(self) -> Tuple[str, int]:
        """
        Determine exact market session and minutes since key events
        """
        now = datetime.now(self.eastern)
        current_time = now.time()
        
        # Define key market times
        pre_market_start = time(4, 0)
        earnings_window = time(7, 0)
        critical_premarket = time(8, 0)
        data_release = time(8, 30)
        final_prep = time(9, 0)
        market_open = time(9, 30)
        momentum_end = time(10, 30)
        market_close = time(16, 0)
        
        # Calculate minutes since market open
        market_open_dt = now.replace(hour=9, minute=30, second=0)
        minutes_since_open = (now - market_open_dt).seconds // 60 if now >= market_open_dt else -1
        
        # Determine session
        if pre_market_start <= current_time < earnings_window:
            return 'early_premarket', -1
        elif earnings_window <= current_time < critical_premarket:
            return 'earnings_window', -1  # GOLDEN TIME
        elif critical_premarket <= current_time < data_release:
            return 'critical_premarket', -1
        elif data_release <= current_time < final_prep:
            return 'data_release', -1  # Economic data
        elif final_prep <= current_time < market_open:
            return 'final_prep', -1
        elif market_open <= current_time < momentum_end:
            return 'opening_momentum', minutes_since_open
        elif momentum_end <= current_time < market_close:
            return 'regular_hours', minutes_since_open
        else:
            return 'closed', -1
    
    async def scan_true_early_movers(self) -> List[Dict]:
        """
        Find stocks JUST starting to move (0.5-3% only)
        This is the CORE function for catching moves early
        """
        session, minutes_since_open = self.get_market_session()
        
        if session == 'closed':
            return []
        
        early_movers = []
        
        # Get appropriate thresholds for current session
        if session in ['early_premarket', 'earnings_window', 'critical_premarket']:
            thresholds = self.early_thresholds['pre_market']
        elif session == 'opening_momentum' and minutes_since_open <= 5:
            thresholds = self.early_thresholds['opening_surge']
        else:
            thresholds = self.early_thresholds['market_hours']
        
        logger.info(f"Scanning for {session} movers (range: {thresholds['min_move']*100:.1f}-{thresholds['max_move']*100:.1f}%)")
        
        try:
            # Priority scan list based on session
            if session == 'earnings_window':
                # Focus on likely earnings movers
                scan_list = await self._get_earnings_watchlist()
            elif session == 'opening_momentum':
                # Focus on pre-market leaders
                scan_list = await self._get_premarket_leaders()
            else:
                # General high-volume stocks
                scan_list = await self._get_volume_leaders()
            
            # Check each stock for EARLY movement
            for symbol in scan_list[:100]:  # Top 100 candidates
                try:
                    movement_data = await self._check_early_movement(
                        symbol, 
                        thresholds,
                        session
                    )
                    
                    if movement_data['is_early']:
                        early_movers.append(movement_data)
                        
                except Exception as e:
                    continue
            
            # Sort by opportunity score
            early_movers.sort(key=lambda x: x['opportunity_score'], reverse=True)
            
            # Log findings
            if early_movers:
                logger.info(f"Found {len(early_movers)} TRUE early movers:")
                for mover in early_movers[:5]:
                    logger.info(f"  {mover['symbol']}: {mover['price_change']:.2%} move, "
                              f"started {mover['minutes_since_start']} mins ago")
            
        except Exception as e:
            logger.error(f"Error in early mover scan: {e}")
        
        return early_movers[:20]  # Top 20 truly early movers
    
    async def _check_early_movement(self, symbol: str, thresholds: Dict, session: str) -> Dict:
        """
        Determine if a stock is TRULY in early stages of a move
        """
        try:
            # Get current snapshot
            snapshot = self.api.get_snapshot(symbol)
            
            if not snapshot or not snapshot.minute_bar:
                return {'is_early': False, 'symbol': symbol}
            
            current_price = snapshot.minute_bar.c
            current_volume = snapshot.minute_bar.v
            
            # Get previous close
            prev_close = snapshot.prev_daily_bar.c if snapshot.prev_daily_bar else 0
            if prev_close == 0:
                return {'is_early': False, 'symbol': symbol}
            
            # Calculate price change
            price_change = (current_price - prev_close) / prev_close
            
            # CHECK 1: Is move in early range?
            if not (thresholds['min_move'] <= abs(price_change) <= thresholds['max_move']):
                return {'is_early': False, 'symbol': symbol}
            
            # CHECK 2: When did move start? (Critical for early detection)
            move_start_time = await self._detect_move_start(symbol, current_price, prev_close)
            minutes_since_start = (datetime.now(self.eastern) - move_start_time).seconds // 60
            
            # CHECK 3: Is volume confirming but not extreme yet?
            avg_volume = snapshot.prev_daily_bar.v / 390 if snapshot.prev_daily_bar else 0
            volume_ratio = current_volume / max(avg_volume * 5, 1)  # 5-min comparison
            
            if not (thresholds['volume_threshold'] <= volume_ratio <= 5):
                return {'is_early': False, 'symbol': symbol}
            
            # CHECK 4: Additional early indicators
            early_score = 0
            signals = []
            
            # Move started recently (within 30 mins)
            if minutes_since_start <= 30:
                early_score += 30
                signals.append(f"Move started {minutes_since_start} mins ago")
            
            # First breakout of the day
            if await self._is_first_breakout(symbol, current_price):
                early_score += 25
                signals.append("First breakout")
            
            # Pre-market or early market session
            if session in ['earnings_window', 'critical_premarket', 'opening_momentum']:
                early_score += 20
                signals.append(f"Prime time: {session}")
            
            # News catalyst check (but not required)
            news_data = await self._check_recent_catalyst(symbol)
            if news_data['has_catalyst']:
                early_score += 25
                signals.append(news_data['catalyst_type'])
            
            # Volume acceleration (increasing each bar)
            if await self._check_volume_acceleration(symbol):
                early_score += 20
                signals.append("Volume accelerating")
            
            # Calculate opportunity score
            opportunity_score = early_score
            
            # Boost score for perfect conditions
            if price_change > 0 and volume_ratio > 2 and minutes_since_start <= 15:
                opportunity_score *= 1.5
            
            # This is a TRUE early mover
            if early_score >= 50:
                return {
                    'is_early': True,
                    'symbol': symbol,
                    'price_change': price_change,
                    'current_price': current_price,
                    'volume_ratio': volume_ratio,
                    'minutes_since_start': minutes_since_start,
                    'move_start_time': move_start_time.isoformat(),
                    'session': session,
                    'signals': signals,
                    'opportunity_score': opportunity_score,
                    'entry_price': current_price,
                    'stop_loss': current_price * (0.98 if price_change > 0 else 1.02),
                    'target_1': current_price * (1.05 if price_change > 0 else 0.95),
                    'target_2': current_price * (1.10 if price_change > 0 else 0.90),
                    'expected_continuation': self._estimate_continuation(price_change, volume_ratio, session)
                }
            
        except Exception as e:
            logger.error(f"Error checking {symbol}: {e}")
        
        return {'is_early': False, 'symbol': symbol}
    
    async def _detect_move_start(self, symbol: str, current_price: float, prev_close: float) -> datetime:
        """
        Detect when the current move actually started
        Critical for determining if we're truly early
        """
        try:
            # Get recent minute bars
            now = datetime.now(self.eastern)
            start_time = now - timedelta(hours=2)
            
            bars = self.api.get_bars(
                symbol,
                tradeapi.TimeFrame.Minute,
                start=start_time.isoformat(),
                end=now.isoformat()
            ).df
            
            if len(bars) < 5:
                return now - timedelta(minutes=5)
            
            # Find when price started moving from prev_close
            threshold_move = 0.005  # 0.5% is start of move
            
            for i in range(len(bars) - 1, -1, -1):
                bar_price = bars.iloc[i]['close']
                price_change = abs((bar_price - prev_close) / prev_close)
                
                if price_change < threshold_move:
                    # This is before the move started
                    if i < len(bars) - 1:
                        # Move started at next bar
                        return bars.index[i + 1].to_pydatetime()
                    break
            
            # Default to 30 mins ago if can't determine
            return now - timedelta(minutes=30)
            
        except:
            return datetime.now(self.eastern) - timedelta(minutes=15)
    
    async def _is_first_breakout(self, symbol: str, current_price: float) -> bool:
        """
        Check if this is the first breakout of the day
        First breakouts are more likely to continue
        """
        try:
            # Get today's bars
            today_start = datetime.now(self.eastern).replace(hour=4, minute=0, second=0)
            
            bars = self.api.get_bars(
                symbol,
                tradeapi.TimeFrame.Minute,
                start=today_start.isoformat(),
                limit=500
            ).df
            
            if len(bars) < 30:
                return True  # Not enough data, assume first
            
            # Check if price has been relatively flat until now
            price_std = bars['close'].iloc[:-10].std()  # Exclude last 10 mins
            avg_price = bars['close'].iloc[:-10].mean()
            
            if avg_price > 0:
                normalized_std = price_std / avg_price
                
                # Low volatility until now = first breakout
                if normalized_std < 0.003:  # Less than 0.3% std dev
                    return True
            
        except:
            pass
        
        return False
    
    async def _check_volume_acceleration(self, symbol: str) -> bool:
        """
        Check if volume is accelerating (each bar > previous)
        Early sign of sustained move
        """
        try:
            # Get last 5 minute bars
            bars = self.api.get_bars(
                symbol,
                tradeapi.TimeFrame.Minute,
                limit=5
            ).df
            
            if len(bars) >= 3:
                volumes = bars['volume'].values
                
                # Check if increasing
                increasing = all(volumes[i] < volumes[i+1] for i in range(len(volumes)-1))
                
                # Or at least trending up
                if not increasing:
                    # Check if trend is up
                    avg_early = np.mean(volumes[:2])
                    avg_late = np.mean(volumes[-2:])
                    trending_up = avg_late > avg_early * 1.5
                    
                    return trending_up
                
                return increasing
                
        except:
            pass
        
        return False
    
    async def _check_recent_catalyst(self, symbol: str) -> Dict:
        """
        Quick check for catalysts (not required but boosts score)
        """
        try:
            # Check news in last 4 hours (pre-market + morning)
            news = self.api.get_news(symbol=symbol, limit=5)
            
            if news:
                latest = news[0]
                time_diff = (datetime.now(pytz.UTC) - latest.created_at).seconds / 3600
                
                if time_diff <= 4:
                    # Categorize catalyst
                    headline = latest.headline.lower()
                    
                    if any(word in headline for word in ['earnings', 'beat', 'raises']):
                        return {'has_catalyst': True, 'catalyst_type': 'earnings'}
                    elif any(word in headline for word in ['fda', 'approval', 'approved']):
                        return {'has_catalyst': True, 'catalyst_type': 'fda'}
                    elif any(word in headline for word in ['upgrade', 'buy rating']):
                        return {'has_catalyst': True, 'catalyst_type': 'upgrade'}
                    else:
                        return {'has_catalyst': True, 'catalyst_type': 'news'}
                        
        except:
            pass
        
        return {'has_catalyst': False, 'catalyst_type': None}
    
    def _estimate_continuation(self, current_move: float, volume_ratio: float, session: str) -> float:
        """
        Estimate how much further the stock might move
        """
        base_continuation = abs(current_move) * 3  # Expect 3x current move
        
        # Adjust based on factors
        if volume_ratio > 3:
            base_continuation *= 1.5
        
        if session in ['earnings_window', 'opening_momentum']:
            base_continuation *= 1.3
        
        # Cap at reasonable levels
        return min(base_continuation, 0.20)  # Max 20% expected
    
    async def _get_earnings_watchlist(self) -> List[str]:
        """
        Get stocks with earnings today/tomorrow
        """
        # This would integrate with earnings calendar API
        # For now, return common earnings movers
        return ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META']
    
    async def _get_premarket_leaders(self) -> List[str]:
        """
        Get current pre-market leaders
        """
        try:
            # Get all tradeable assets
            assets = self.api.list_assets(status='active', asset_class='us_equity')
            tradeable = [a.symbol for a in assets if a.tradable][:200]
            
            # Get snapshots and find movers
            movers = []
            for batch in [tradeable[i:i+50] for i in range(0, len(tradeable), 50)]:
                try:
                    snapshots = self.api.get_snapshots(batch)
                    for symbol, snapshot in snapshots.items():
                        if snapshot and snapshot.minute_bar and snapshot.prev_daily_bar:
                            prev_close = snapshot.prev_daily_bar.c
                            current = snapshot.minute_bar.c
                            change = (current - prev_close) / prev_close
                            
                            if 0.005 <= abs(change) <= 0.05:  # Moving but not too much
                                movers.append(symbol)
                except:
                    continue
            
            return movers
            
        except:
            return []
    
    async def _get_volume_leaders(self) -> List[str]:
        """
        Get stocks with increasing volume
        """
        # Default high-volume stocks that move
        return ['SPY', 'QQQ', 'TSLA', 'NVDA', 'AMD', 'AAPL', 'MSFT', 'META', 
                'AMZN', 'GOOGL', 'SOFI', 'PLTR', 'NIO', 'RIVN', 'LCID']
    
    async def get_priority_trades(self) -> List[Dict]:
        """
        Main method: Get the best early-stage trades RIGHT NOW
        """
        session, minutes = self.get_market_session()
        
        logger.info(f"Session: {session}, Minutes since open: {minutes}")
        
        all_opportunities = []
        
        # 1. Get truly early movers (primary focus)
        early_movers = await self.scan_true_early_movers()
        all_opportunities.extend(early_movers)
        
        # 2. Session-specific additions
        if session == 'earnings_window':
            logger.info("🎯 EARNINGS WINDOW - Maximum priority!")
            # Extra aggressive scanning during earnings
            
        elif session == 'opening_momentum' and minutes <= 5:
            logger.info("🔥 FIRST 5 MINUTES - Critical time!")
            # Most important 5 minutes of the day
            
        elif session == 'data_release':
            logger.info("📊 Economic data window - Watch for market moves")
        
        # Sort by opportunity score
        all_opportunities.sort(key=lambda x: x.get('opportunity_score', 0), reverse=True)
        
        # Return top opportunities
        return all_opportunities[:10]


# Integration helper
class EarlyDetectionIntegration:
    """
    Easy integration with your existing bot
    """
    
    def __init__(self, api):
        self.scanner = OptimizedEarlyDetectionScanner(api)
        
    async def should_enter_position(self, symbol: str, data: Dict) -> bool:
        """
        Determine if this is truly early enough to enter
        """
        # Key criteria for entry
        if data.get('minutes_since_start', 999) > 30:
            logger.warning(f"{symbol}: Move started {data['minutes_since_start']} mins ago - TOO LATE")
            return False
        
        if abs(data.get('price_change', 0)) > 0.05:
            logger.warning(f"{symbol}: Already up {data['price_change']:.1%} - TOO EXTENDED")
            return False
        
        if data.get('opportunity_score', 0) < 50:
            logger.info(f"{symbol}: Score {data['opportunity_score']} - Not strong enough")
            return False
        
        logger.info(f"✅ {symbol}: TRULY EARLY - Enter position!")
        return True
    
    async def get_position_size(self, data: Dict) -> float:
        """
        Size position based on how early we are
        """
        minutes_since_start = data.get('minutes_since_start', 30)
        
        if minutes_since_start <= 5:
            return 0.08  # 8% - Very early, high conviction
        elif minutes_since_start <= 15:
            return 0.05  # 5% - Early
        elif minutes_since_start <= 30:
            return 0.03  # 3% - Getting late
        else:
            return 0.02  # 2% - Minimal position


if __name__ == "__main__":
    import asyncio
    
    async def test():
        api = tradeapi.REST(
            os.getenv('ALPACA_API_KEY'),
            os.getenv('ALPACA_SECRET_KEY'),
            os.getenv('ALPACA_BASE_URL')
        )
        
        scanner = OptimizedEarlyDetectionScanner(api)
        
        print("\n🎯 OPTIMIZED EARLY DETECTION TEST 🎯\n")
        
        # Get current session
        session, minutes = scanner.get_market_session()
        print(f"Current Session: {session}")
        if minutes >= 0:
            print(f"Minutes since market open: {minutes}")
        
        print("\nScanning for TRULY early opportunities...")
        print("(Looking for 0.5-3% moves, not 5%+ chasers)\n")
        
        # Get early opportunities
        opportunities = await scanner.get_priority_trades()
        
        if opportunities:
            print(f"Found {len(opportunities)} early-stage opportunities:\n")
            
            for i, opp in enumerate(opportunities[:5], 1):
                print(f"{i}. {opp['symbol']}")
                print(f"   Move: {opp['price_change']:.2%}")
                print(f"   Started: {opp['minutes_since_start']} minutes ago")
                print(f"   Volume: {opp['volume_ratio']:.1f}x normal")
                print(f"   Score: {opp['opportunity_score']:.0f}")
                print(f"   Signals: {', '.join(opp['signals'])}")
                print(f"   Expected continuation: {opp['expected_continuation']:.1%}")
                print()
        else:
            print("No early opportunities found right now")
            print("This is normal outside of market hours or during quiet periods")
    
    asyncio.run(test())