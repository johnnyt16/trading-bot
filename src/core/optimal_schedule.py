#!/usr/bin/env python3
"""
optimal_schedule.py - The REAL timeline for catching moves early
Configured for EST (New York) timezone where your bot runs
"""

from datetime import datetime, time, timedelta
import pytz
from typing import Dict, List
import schedule
import time as time_module
from loguru import logger

class OptimalTradingSchedule:
    """
    The correct schedule to catch moves EARLY
    All times in EST (your DigitalOcean server timezone)
    """
    
    def __init__(self):
        self.est = pytz.timezone('US/Eastern')
        self.trading_sessions = {
            'pre_pre_market': {
                'start': time(4, 0),   # 4:00 AM
                'end': time(6, 0),     # 6:00 AM
                'description': 'Early birds and European influence'
            },
            'active_pre_market': {
                'start': time(6, 0),   # 6:00 AM
                'end': time(8, 0),     # 8:00 AM
                'description': 'News drops, earnings releases'
            },
            'critical_pre_market': {
                'start': time(8, 0),   # 8:00 AM
                'end': time(9, 30),    # 9:30 AM
                'description': 'Highest volume, final positioning'
            },
            'market_open_surge': {
                'start': time(9, 30),  # 9:30 AM
                'end': time(10, 30),   # 10:30 AM
                'description': 'Opening volatility, biggest moves'
            },
            'late_morning': {
                'start': time(10, 30), # 10:30 AM
                'end': time(12, 0),    # 12:00 PM
                'description': 'Momentum continuation'
            },
            'lunch_lull': {
                'start': time(12, 0),  # 12:00 PM
                'end': time(14, 0),    # 2:00 PM
                'description': 'Low volume, avoid trading'
            },
            'power_hour': {
                'start': time(15, 0),  # 3:00 PM
                'end': time(16, 0),    # 4:00 PM
                'description': 'End of day positioning'
            },
            'after_hours': {
                'start': time(16, 0),  # 4:00 PM
                'end': time(20, 0),    # 8:00 PM
                'description': 'Earnings reactions'
            }
        }
    
    def get_current_session(self) -> str:
        """What trading session are we in?"""
        now = datetime.now(self.est).time()
        
        for session_name, session_info in self.trading_sessions.items():
            if session_info['start'] <= now < session_info['end']:
                return session_name
        
        return 'market_closed'
    
    def get_scan_strategy(self) -> Dict:
        """
        Different strategies for different times
        """
        session = self.get_current_session()
        
        strategies = {
            'pre_pre_market': {
                'scan_frequency': 30,  # Every 30 minutes
                'focus': ['overnight_news', 'european_influence', 'futures'],
                'position_size': 0.02,  # Small, risky time
                'targets': [
                    'Overnight FDA approvals',
                    'European market movers',
                    'Crypto-correlated stocks'
                ]
            },
            'active_pre_market': {
                'scan_frequency': 10,  # Every 10 minutes
                'focus': ['earnings_releases', 'upgrades', 'pre_market_volume'],
                'position_size': 0.04,  # Medium positions
                'targets': [
                    'Earnings beats (7-8 AM releases)',
                    'Analyst upgrades',
                    'Stocks up 2-5% on volume'
                ]
            },
            'critical_pre_market': {
                'scan_frequency': 5,   # Every 5 minutes
                'focus': ['volume_surges', 'breaking_news', 'gap_ups'],
                'position_size': 0.06,  # Larger, more confident
                'targets': [
                    'Gap up stocks with volume',
                    'Breaking news reactions',
                    'Social media explosions'
                ]
            },
            'market_open_surge': {
                'scan_frequency': 1,   # Every minute!
                'focus': ['opening_drives', 'volume_explosions', 'breakouts'],
                'position_size': 0.08,  # Maximum positions
                'targets': [
                    'Opening range breakouts',
                    'Continuation from pre-market',
                    'Surprise movers'
                ]
            }
        }
        
        return strategies.get(session, {
            'scan_frequency': 15,
            'focus': ['general'],
            'position_size': 0.03
        })

class PreMarketScanner:
    """
    Specialized scanner for pre-market opportunities
    """
    
    def __init__(self, api):
        self.api = api
        self.est = pytz.timezone('US/Eastern')
        
    def scan_4am_movers(self) -> List[Dict]:
        """
        4:00 AM - 6:00 AM: Catch the earliest movers
        """
        early_birds = []
        
        # These are usually:
        # - Overnight news reactions
        # - ADRs following European markets
        # - Crypto-related stocks following Bitcoin
        
        logger.info("🌅 4 AM Scan - Looking for overnight catalysts")
        
        # Check stocks that typically move early
        early_movers_watchlist = [
            'TSLA',  # Often moves on China/Europe news
            'NIO', 'XPEV', 'LI',  # Chinese EVs
            'BABA', 'JD', 'PDD',  # Chinese tech
            'MARA', 'RIOT',  # Crypto miners
            'COIN',  # Crypto exchange
            'PLTR',  # Government contracts often announced early
        ]
        
        for symbol in early_movers_watchlist:
            try:
                # Get pre-market quote
                quote = self.api.get_latest_quote(symbol)
                trades = self.api.get_trades(symbol, start=datetime.now() - timedelta(hours=4))
                
                if len(trades) > 100:  # Active in pre-market
                    # Calculate movement
                    # Add to early_birds if moving
                    pass
                    
            except:
                pass
        
        return early_birds
    
    def scan_7am_earnings(self) -> List[Dict]:
        """
        7:00 AM - 8:30 AM: Prime earnings release time
        """
        earnings_movers = []
        
        logger.info("📊 7 AM Scan - Checking earnings releases")
        
        # Most companies release earnings 7:00-8:30 AM
        # This is GOLDEN HOUR for catching earnings pops
        
        # Check earnings calendar
        # Check for stocks with unusual pre-market volume
        # Look for >5% moves on >100k volume
        
        return earnings_movers
    
    def scan_830am_setup(self) -> List[Dict]:
        """
        8:30 AM - 9:25 AM: Final pre-market positioning
        THIS IS CRITICAL - Last chance before open
        """
        final_setups = []
        
        logger.info("🚀 8:30 AM Scan - Final pre-market setups")
        
        # This is when:
        # - Smart money positions
        # - Retail starts paying attention  
        # - Volume really picks up
        # - Economic data drops (8:30 AM exactly)
        
        # Look for:
        # - Stocks up 2-5% with increasing volume
        # - Breakout setups about to trigger
        # - Social media starting to buzz
        
        return final_setups
    
    def scan_925am_final(self) -> List[Dict]:
        """
        9:25 AM - 9:29 AM: LAST 5 MINUTES
        Final scan before market open
        """
        logger.info("⚡ 9:25 AM - FINAL SCAN BEFORE OPEN")
        
        # Get everything set up for market open
        # Identify opening drive candidates
        # Set alerts for breakout levels
        
        return []

class OptimalBotScheduler:
    """
    The complete automated schedule for your bot
    """
    
    def __init__(self):
        self.schedule = OptimalTradingSchedule()
        self.scanner = None  # Initialize with your scanner
        
    def setup_schedule(self):
        """
        Configure the bot's daily schedule
        """
        
        # Pre-market scans
        schedule.every().day.at("04:00").do(self.early_bird_scan)
        schedule.every().day.at("06:00").do(self.active_premarket_scan)
        schedule.every().day.at("07:00").do(self.earnings_scan)
        schedule.every().day.at("08:00").do(self.critical_scan)
        schedule.every().day.at("08:30").do(self.economic_data_scan)
        schedule.every().day.at("09:00").do(self.final_premarket_scan)
        schedule.every().day.at("09:25").do(self.prepare_open)
        
        # Market hours
        schedule.every().day.at("09:30").do(self.market_open_trades)
        schedule.every().day.at("10:00").do(self.momentum_scan)
        schedule.every().day.at("10:30").do(self.scale_positions)
        
        # Avoid lunch
        schedule.every().day.at("12:00").do(self.lunch_pause)
        schedule.every().day.at("14:00").do(self.afternoon_scan)
        
        # Power hour
        schedule.every().day.at("15:00").do(self.power_hour_setup)
        schedule.every().day.at("15:45").do(self.eod_positions)
        
        # After hours
        schedule.every().day.at("16:05").do(self.afterhours_scan)
        
        logger.info("📅 Schedule configured for optimal trading times")
    
    def early_bird_scan(self):
        """4:00 AM - First scan of the day"""
        logger.info("=" * 50)
        logger.info("🌅 4:00 AM - EARLY BIRD SCAN")
        logger.info("=" * 50)
        
        # Light scan - not much volume yet
        # Focus on overnight news
        # Check futures for market direction
        # Small positions only
        
    def active_premarket_scan(self):
        """6:00 AM - Activity picking up"""
        logger.info("📈 6:00 AM - Pre-market getting active")
        
        # More aggressive scanning
        # Look for stocks with growing volume
        # Check European market influence
        
    def earnings_scan(self):
        """7:00 AM - Prime earnings time"""
        logger.info("📊 7:00 AM - EARNINGS SCAN")
        
        # Critical time - many earnings release now
        # Scan every 5 minutes from 7-8:30 AM
        # Look for beats with guidance raises
        
    def critical_scan(self):
        """8:00 AM - High importance scan"""
        logger.info("🎯 8:00 AM - CRITICAL PRE-MARKET SCAN")
        
        # Volume really picking up
        # Smart money positioning
        # Best time to find day's movers
        
    def economic_data_scan(self):
        """8:30 AM - Economic data releases"""
        logger.info("📰 8:30 AM - Economic data check")
        
        # CPI, Jobs data, etc. release at 8:30
        # Can move entire market
        # Adjust strategy based on data
        
    def prepare_open(self):
        """9:25 AM - Final preparation"""
        logger.info("⚡ 9:25 AM - PREPARING FOR OPEN")
        
        # Set all orders
        # Final scan
        # Get ready for 9:30 chaos
        
    def market_open_trades(self):
        """9:30 AM - MARKET OPEN"""
        logger.info("🔔 9:30 AM - MARKET OPEN - EXECUTE TRADES")
        
        # Most important time of day
        # Execute Tier 1 setups
        # Maximum position sizes
        # Scan every minute for first 30 mins

# Actual implementation for your bot
def get_optimal_scan_frequency():
    """
    How often to scan based on time of day
    """
    now = datetime.now(pytz.timezone('US/Eastern'))
    hour = now.hour
    minute = now.minute
    
    # Pre-market (4 AM - 9:30 AM)
    if 4 <= hour < 6:
        return 1800  # Every 30 minutes (not much happening)
    
    elif 6 <= hour < 8:
        return 600   # Every 10 minutes (warming up)
    
    elif 8 <= hour < 9:
        return 300   # Every 5 minutes (critical time)
    
    elif hour == 9 and minute < 30:
        return 60    # Every minute (about to open!)
    
    # Market hours (9:30 AM - 4 PM)
    elif hour == 9 and minute >= 30:
        return 30    # Every 30 seconds first 30 mins!
    
    elif 10 <= hour < 11:
        return 60    # Every minute (high activity)
    
    elif 11 <= hour < 14:
        return 300   # Every 5 minutes (lunch lull)
    
    elif 14 <= hour < 15:
        return 180   # Every 3 minutes (afternoon)
    
    elif 15 <= hour < 16:
        return 60    # Every minute (power hour)
    
    # After hours
    elif 16 <= hour < 20:
        return 600   # Every 10 minutes
    
    else:
        return 3600  # Every hour (market closed)

if __name__ == "__main__":
    print("\n⏰ OPTIMAL TRADING SCHEDULE (EST) ⏰\n")
    print("Your bot should run on this schedule:\n")
    
    schedule_items = [
        ("4:00 AM", "Wake up - Check overnight news", "🌅"),
        ("6:00 AM", "Active scanning begins", "📈"),
        ("7:00 AM", "CRITICAL - Earnings releases", "📊"),
        ("8:00 AM", "Heavy pre-market scanning", "🎯"),
        ("8:30 AM", "Economic data + Final prep", "📰"),
        ("9:00 AM", "High-frequency scanning", "⚡"),
        ("9:25 AM", "Final positions before open", "🚨"),
        ("9:30 AM", "MARKET OPEN - Maximum activity", "🔔"),
        ("10:00 AM", "Momentum continuation", "🚀"),
        ("10:30 AM", "Scale winners/cut losers", "⚖️"),
        ("12:00 PM", "Reduce activity (lunch)", "🍽️"),
        ("3:00 PM", "Power hour preparation", "💪"),
        ("3:45 PM", "End of day positioning", "🏁"),
        ("4:00 PM", "Market close - After-hours scan", "🌙"),
    ]
    
    for time, description, emoji in schedule_items:
        print(f"{emoji} {time:8s} - {description}")
    
    print("\n" + "=" * 50)
    print("KEY INSIGHTS:")
    print("=" * 50)
    print("""
    1. 4:00 AM is NOT too early - Big moves start then
    2. 7:00-8:30 AM is GOLDEN HOUR for earnings
    3. 8:30 AM exactly - Economic data drops
    4. 9:25-9:35 AM - Most critical 10 minutes of the day
    5. 10:30 AM - Last chance for momentum plays
    6. 12-2 PM - Usually dead, reduce scanning
    7. 3:00 PM - Power hour can bring surprises
    
    Your DigitalOcean server in NY is PERFECTLY located
    for this schedule - same timezone as the market!
    """)
    
    print(f"\nRight now, you should be scanning every {get_optimal_scan_frequency()} seconds")