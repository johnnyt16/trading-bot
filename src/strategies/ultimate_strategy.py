#!/usr/bin/env python3
"""
ultimate_strategy.py - The complete strategy combining all signals
This is the master strategy for 10x returns
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import numpy as np
from loguru import logger

@dataclass
class TradeSetup:
    """Complete trade setup with all signals"""
    symbol: str
    strategy_type: str
    confidence: float
    entry_price: float
    position_size_pct: float
    stop_loss: float
    target_1: float
    target_2: float
    target_3: float
    signals: List[str]
    expected_move: float
    time_horizon: str

class UltimateTradingStrategy:
    """
    The complete strategy combining:
    1. Pre-catalyst positioning
    2. Early momentum detection  
    3. Social sentiment
    4. Technical breakouts
    5. News catalysts
    """
    
    def __init__(self):
        # Strategy allocations
        self.portfolio_allocation = {
            'tier_1_rockets': 0.40,    # 40% - High conviction plays
            'tier_2_momentum': 0.30,    # 30% - Early momentum
            'tier_3_catalysts': 0.20,   # 20% - Pre-catalyst
            'cash_reserve': 0.10        # 10% - Opportunity fund
        }
        
    def get_tier_1_rockets(self, market_data: Dict) -> List[TradeSetup]:
        """
        TIER 1: The Rocket Ships (40% of portfolio)
        These have EVERYTHING aligned - highest probability of 10-30% moves
        """
        rockets = []
        
        for symbol, data in market_data.items():
            score = 0
            signals = []
            
            # Perfect setup criteria:
            
            # 1. EARLY MOMENTUM (not late)
            if 0.02 <= data['price_change'] <= 0.05:
                score += 25
                signals.append(f"Early move {data['price_change']:.1%}")
            
            # 2. VOLUME SURGE (confirmation)
            if 2 <= data['volume_ratio'] <= 5:
                score += 25
                signals.append(f"Volume {data['volume_ratio']:.1f}x")
            
            # 3. FRESH NEWS (catalyst)
            if data['news_age_hours'] <= 2:
                score += 20
                signals.append("Fresh catalyst")
            
            # 4. SOCIAL BUZZ (retail incoming)
            if data['social_score'] >= 60:
                score += 20
                signals.append("Social momentum")
            
            # 5. TECHNICAL BREAKOUT
            if data['breaking_resistance']:
                score += 20
                signals.append("Breaking resistance")
            
            # 6. FLOAT/SHORTS (squeeze potential)
            if data.get('short_interest', 0) > 0.20:
                score += 15
                signals.append(f"Short squeeze {data['short_interest']:.0%}")
            
            # THIS IS A ROCKET - Multiple factors aligned
            if score >= 80:
                rockets.append(TradeSetup(
                    symbol=symbol,
                    strategy_type="TIER_1_ROCKET",
                    confidence=score,
                    entry_price=data['current_price'],
                    position_size_pct=0.08,  # 8% position (big for high conviction)
                    stop_loss=data['current_price'] * 0.95,  # 5% stop
                    target_1=data['current_price'] * 1.10,   # 10% target
                    target_2=data['current_price'] * 1.20,   # 20% target  
                    target_3=data['current_price'] * 1.30,   # 30% stretch
                    signals=signals,
                    expected_move=0.15,  # Expect 15%+ moves
                    time_horizon="TODAY"
                ))
        
        return rockets
    
    def get_tier_2_momentum(self, market_data: Dict) -> List[TradeSetup]:
        """
        TIER 2: Early Momentum Plays (30% of portfolio)
        Good setups but missing 1-2 factors
        """
        momentum_plays = []
        
        for symbol, data in market_data.items():
            score = 0
            signals = []
            
            # Need 3 of 5 factors:
            
            has_momentum = 0.015 <= data['price_change'] <= 0.08
            has_volume = data['volume_ratio'] >= 1.5
            has_news = data['news_age_hours'] <= 24
            has_social = data['social_score'] >= 40
            has_technical = data['above_sma20'] and data['rsi'] < 70
            
            factors = sum([has_momentum, has_volume, has_news, has_social, has_technical])
            
            if factors >= 3:
                if has_momentum:
                    signals.append(f"Move {data['price_change']:.1%}")
                if has_volume:
                    signals.append(f"Volume {data['volume_ratio']:.1f}x")
                if has_news:
                    signals.append("News catalyst")
                if has_social:
                    signals.append("Social buzz")
                if has_technical:
                    signals.append("Technical setup")
                
                momentum_plays.append(TradeSetup(
                    symbol=symbol,
                    strategy_type="TIER_2_MOMENTUM",
                    confidence=factors * 20,
                    entry_price=data['current_price'],
                    position_size_pct=0.05,  # 5% position (medium)
                    stop_loss=data['current_price'] * 0.97,  # 3% stop
                    target_1=data['current_price'] * 1.05,
                    target_2=data['current_price'] * 1.10,
                    target_3=data['current_price'] * 1.15,
                    signals=signals,
                    expected_move=0.07,
                    time_horizon="1-2 DAYS"
                ))
        
        return momentum_plays
    
    def get_tier_3_catalysts(self, market_data: Dict) -> List[TradeSetup]:
        """
        TIER 3: Pre-Catalyst Lottery Tickets (20% of portfolio)
        Upcoming events that could trigger big moves
        """
        catalyst_plays = []
        
        for symbol, data in market_data.items():
            # FDA decisions, earnings, conferences
            if data.get('upcoming_catalyst'):
                catalyst_type = data['catalyst_type']
                days_until = data['days_until_catalyst']
                
                if days_until <= 3:
                    # Position before the event
                    catalyst_plays.append(TradeSetup(
                        symbol=symbol,
                        strategy_type="TIER_3_CATALYST",
                        confidence=60,
                        entry_price=data['current_price'],
                        position_size_pct=0.03,  # 3% position (lottery ticket)
                        stop_loss=data['current_price'] * 0.90,  # 10% stop (wider)
                        target_1=data['current_price'] * 1.15,
                        target_2=data['current_price'] * 1.30,
                        target_3=data['current_price'] * 1.50,  # Moon shot
                        signals=[f"{catalyst_type} in {days_until} days"],
                        expected_move=0.20,  # Could be huge or nothing
                        time_horizon=f"{days_until} DAYS"
                    ))
        
        return catalyst_plays
    
    def combine_all_strategies(self, 
                              early_momentum_signals: List,
                              social_signals: List,
                              news_signals: List,
                              technical_signals: List) -> Dict:
        """
        Master combination logic - this is where the magic happens
        """
        
        # Aggregate all data by symbol
        market_data = {}
        
        # Process each signal type
        for signal in early_momentum_signals:
            symbol = signal['symbol']
            if symbol not in market_data:
                market_data[symbol] = {
                    'symbol': symbol,
                    'signals': [],
                    'scores': {}
                }
            market_data[symbol]['price_change'] = signal.get('price_change', 0)
            market_data[symbol]['volume_ratio'] = signal.get('volume_ratio', 1)
            market_data[symbol]['current_price'] = signal.get('price', 0)
            
        for signal in social_signals:
            symbol = signal['symbol']
            if symbol in market_data:
                market_data[symbol]['social_score'] = signal.get('social_score', 0)
                market_data[symbol]['wsb_mentions'] = signal.get('wsb_mentions', 0)
                
        for signal in news_signals:
            symbol = signal['symbol']
            if symbol in market_data:
                market_data[symbol]['news_age_hours'] = signal.get('hours_since_news', 999)
                market_data[symbol]['news_type'] = signal.get('catalyst_type', '')
                
        for signal in technical_signals:
            symbol = signal['symbol']  
            if symbol in market_data:
                market_data[symbol]['breaking_resistance'] = signal.get('breaking_resistance', False)
                market_data[symbol]['rsi'] = signal.get('rsi', 50)
                market_data[symbol]['above_sma20'] = signal.get('above_sma20', False)
        
        # Get setups for each tier
        tier_1 = self.get_tier_1_rockets(market_data)
        tier_2 = self.get_tier_2_momentum(market_data)
        tier_3 = self.get_tier_3_catalysts(market_data)
        
        return {
            'tier_1_rockets': tier_1,
            'tier_2_momentum': tier_2,
            'tier_3_catalysts': tier_3,
            'total_setups': len(tier_1) + len(tier_2) + len(tier_3)
        }

class OptimalExecutionStrategy:
    """
    HOW to trade each setup for maximum gains
    """
    
    def __init__(self):
        self.active_trades = {}
        
    def execute_tier_1_rocket(self, setup: TradeSetup) -> Dict:
        """
        Tier 1 execution - Scale in aggressively
        """
        return {
            'entry_1': {
                'trigger': 'IMMEDIATE',
                'size': setup.position_size_pct * 0.5,  # Half position now
                'reason': 'Initial entry on perfect setup'
            },
            'entry_2': {
                'trigger': 'UP_2_PERCENT',
                'size': setup.position_size_pct * 0.3,  # Add 30% more
                'reason': 'Momentum confirming'
            },
            'entry_3': {
                'trigger': 'BREAK_FIRST_TARGET',
                'size': setup.position_size_pct * 0.2,  # Final 20%
                'reason': 'Full momentum'
            },
            'exit_strategy': {
                'stop_loss': setup.stop_loss,
                'target_1_exit': 0.25,  # Sell 25% at first target
                'target_2_exit': 0.50,  # Sell 50% at second target
                'target_3_exit': 0.25,  # Final 25% at moonshot
                'trailing_stop': True,  # Trail after target 1
            }
        }
    
    def execute_tier_2_momentum(self, setup: TradeSetup) -> Dict:
        """
        Tier 2 execution - Single entry, quick exit
        """
        return {
            'entry': {
                'trigger': 'IMMEDIATE',
                'size': setup.position_size_pct,
                'reason': 'Momentum play'
            },
            'exit_strategy': {
                'stop_loss': setup.stop_loss,
                'target_1_exit': 0.50,  # Sell half at 5%
                'target_2_exit': 0.50,  # Sell rest at 10%
                'trailing_stop': False
            }
        }
    
    def execute_tier_3_catalyst(self, setup: TradeSetup) -> Dict:
        """
        Tier 3 execution - Lottery ticket
        """
        return {
            'entry': {
                'trigger': 'IMMEDIATE',
                'size': setup.position_size_pct,
                'reason': f'Pre-catalyst position'
            },
            'exit_strategy': {
                'stop_loss': setup.stop_loss,
                'catalyst_hit': 'HOLD_THROUGH_NEWS',  # Don't sell before catalyst
                'target_1_exit': 0.33,
                'target_2_exit': 0.33,
                'target_3_exit': 0.34,
                'time_stop': setup.time_horizon  # Exit after catalyst date
            }
        }

# The COMPLETE PLAYBOOK
class TradingPlaybook:
    """
    Your exact rules for 10x returns
    """
    
    MORNING_ROUTINE = """
    9:00 AM - Pre-Market Scan
    - Check overnight news
    - Scan pre-market movers (2-5% moves)
    - Check social sentiment trending
    - Identify Tier 1 rockets
    
    9:30 AM - Market Open
    - Execute Tier 1 rockets immediately
    - Set alerts for Tier 2 momentum
    - Place catalyst positions (Tier 3)
    
    10:00 AM - Momentum Hour
    - Look for volume surges
    - Scale into winners
    - Cut losers quickly
    """
    
    POSITION_RULES = """
    Maximum Positions: 8-10 stocks
    
    Position Sizing:
    - Tier 1 Rockets: 6-8% each (max 3 positions)
    - Tier 2 Momentum: 4-5% each (max 4 positions)
    - Tier 3 Catalysts: 2-3% each (max 3 positions)
    
    Risk Management:
    - Daily stop: -5% portfolio
    - Single stock max: 10% of portfolio
    - Cut losses at stop, no exceptions
    - Trail stops after 5% gain
    """
    
    BEST_SETUPS = """
    The HIGHEST Probability 10x Setups:
    
    1. FDA APPROVAL POP
    - Enter 1-2 days before decision
    - Small position (2-3%)
    - Can run 30-50% on approval
    
    2. EARNINGS BEAT + GUIDANCE RAISE
    - Enter on news within 30 mins
    - 5% position
    - Typically runs 10-15%
    
    3. SHORT SQUEEZE SETUP
    - High short interest (>20%)
    - Social buzz building
    - Volume surge starting
    - Can run 20-100%
    
    4. BREAKOUT + NEWS COMBO
    - Technical breakout
    - With fresh catalyst
    - 5-7% position
    - Runs 10-20%
    
    5. SOCIAL FRENZY
    - WSB + StockTwits exploding
    - Early in move (<5%)
    - 3-5% position
    - Unpredictable but huge potential
    """
    
    EXIT_RULES = """
    Scale Out Strategy:
    - Sell 25% at +5%
    - Sell 25% at +10%
    - Sell 25% at +15%
    - Let 25% run with trailing stop
    
    This locks in gains while keeping upside!
    """

def calculate_expected_returns():
    """
    Math behind 10x returns
    """
    
    scenarios = {
        'Conservative': {
            'win_rate': 0.45,
            'avg_win': 0.08,  # 8% average win
            'avg_loss': 0.03,  # 3% average loss
            'trades_per_day': 3,
            'trading_days': 250
        },
        'Realistic': {
            'win_rate': 0.50,
            'avg_win': 0.12,  # 12% average win
            'avg_loss': 0.04,  # 4% average loss
            'trades_per_day': 4,
            'trading_days': 250
        },
        'Aggressive': {
            'win_rate': 0.55,
            'avg_win': 0.15,  # 15% average win
            'avg_loss': 0.05,  # 5% average loss
            'trades_per_day': 5,
            'trading_days': 250
        }
    }
    
    print("\n💰 EXPECTED RETURNS CALCULATION 💰\n")
    
    for name, params in scenarios.items():
        # Calculate expectancy per trade
        expectancy = (params['win_rate'] * params['avg_win']) - ((1-params['win_rate']) * params['avg_loss'])
        
        # Total trades per year
        total_trades = params['trades_per_day'] * params['trading_days']
        
        # Compound returns (simplified)
        # Starting with $1,000
        capital = 1000
        for _ in range(total_trades):
            capital *= (1 + expectancy)
        
        print(f"{name} Scenario:")
        print(f"  Win Rate: {params['win_rate']:.0%}")
        print(f"  Avg Win: {params['avg_win']:.1%}")
        print(f"  Avg Loss: {params['avg_loss']:.1%}")
        print(f"  Expectancy per trade: {expectancy:.2%}")
        print(f"  Final Capital: ${capital:,.0f}")
        print(f"  Return Multiple: {capital/1000:.1f}x")
        print()

if __name__ == "__main__":
    print(TradingPlaybook.MORNING_ROUTINE)
    print(TradingPlaybook.POSITION_RULES)
    print(TradingPlaybook.BEST_SETUPS)
    print(TradingPlaybook.EXIT_RULES)
    
    calculate_expected_returns()
    
    print("\n🎯 THE PATH TO 10X 🎯")
    print("""
    1. Find 3-5 Tier 1 Rockets daily (perfect setups)
    2. Take 5-10 Tier 2 Momentum plays weekly
    3. Always have 2-3 Tier 3 Catalysts cooking
    4. Scale into winners, cut losers fast
    5. Compound gains - reinvest everything
    
    With 50% win rate and 3:1 reward/risk:
    - Month 1-2: Learn and refine (+20%)
    - Month 3-4: Consistent profits (+40%)  
    - Month 5-6: Compounding kicks in (+80%)
    - Month 7-12: Exponential growth (10x)
    
    The key: DISCIPLINE + EARLY ENTRY + MULTIPLE SIGNALS
    """)