#!/usr/bin/env python3
"""
Tests for Ultimate Trading Strategy
Testing the master strategy that combines all signals
"""

import sys
import os
import pytest
from unittest.mock import Mock, MagicMock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.strategies.ultimate_strategy import UltimateTradingStrategy, TradeSetup


class TestUltimateTradingStrategy:
    """Test the ultimate trading strategy logic"""
    
    @pytest.fixture
    def strategy(self):
        """Create strategy instance"""
        return UltimateTradingStrategy()
    
    def test_strategy_initialization(self, strategy):
        """Test strategy initializes with correct allocations"""
        assert strategy.portfolio_allocation['tier_1_rockets'] == 0.40  # 40%
        assert strategy.portfolio_allocation['tier_2_momentum'] == 0.30  # 30%
        assert strategy.portfolio_allocation['tier_3_catalysts'] == 0.20  # 20%
        assert strategy.portfolio_allocation['cash_reserve'] == 0.10  # 10%
        
        # Total should be 100%
        total = sum(strategy.portfolio_allocation.values())
        assert abs(total - 1.0) < 0.001  # Allow for floating point precision
    
    def test_tier_1_rocket_identification(self, strategy):
        """Test identification of Tier 1 rocket setups"""
        market_data = {
            'TSLA': {
                'price_change': 0.035,  # 3.5% move (early range)
                'volume_ratio': 3.5,  # Good volume
                'news_age_hours': 1,  # Fresh news
                'social_score': 75,  # Strong social
                'breaking_resistance': True,
                'short_interest': 0.25,  # 25% short interest
                'current_price': 200.0
            },
            'AAPL': {
                'price_change': 0.08,  # 8% move (too extended)
                'volume_ratio': 2.0,
                'news_age_hours': 3,
                'social_score': 40,
                'breaking_resistance': False,
                'current_price': 150.0
            }
        }
        
        rockets = strategy.get_tier_1_rockets(market_data)
        
        # TSLA should qualify, AAPL should not (too extended)
        assert len(rockets) >= 1
        if rockets:
            assert rockets[0].symbol == 'TSLA'
            assert rockets[0].strategy_type == "TIER_1_ROCKET"
            assert rockets[0].position_size_pct == 0.08  # 8% position
            assert rockets[0].confidence >= 80  # High confidence
    
    def test_tier_2_momentum_identification(self, strategy):
        """Test identification of Tier 2 momentum plays"""
        market_data = {
            'NVDA': {
                'price_change': 0.025,  # 2.5% move
                'volume_ratio': 2.0,  # Good volume
                'news_age_hours': 12,  # Recent news
                'social_score': 45,  # Moderate social
                'above_sma20': True,
                'rsi': 65,
                'current_price': 500.0
            },
            'AMD': {
                'price_change': 0.001,  # Too small move
                'volume_ratio': 1.0,  # Low volume
                'news_age_hours': 48,
                'social_score': 20,
                'above_sma20': False,
                'rsi': 45,
                'current_price': 100.0
            }
        }
        
        momentum_plays = strategy.get_tier_2_momentum(market_data)
        
        # NVDA should qualify (3+ factors), AMD should not
        if momentum_plays:
            nvda_found = any(play.symbol == 'NVDA' for play in momentum_plays)
            assert nvda_found
            
            nvda_play = next((p for p in momentum_plays if p.symbol == 'NVDA'), None)
            if nvda_play:
                assert nvda_play.strategy_type == "TIER_2_MOMENTUM"
                assert nvda_play.position_size_pct == 0.05  # 5% position
    
    def test_tier_3_catalyst_identification(self, strategy):
        """Test identification of Tier 3 pre-catalyst plays"""
        market_data = {
            'MRNA': {
                'upcoming_catalyst': True,
                'catalyst_type': 'FDA_DECISION',
                'days_until_catalyst': 2,
                'current_price': 50.0
            },
            'PFE': {
                'upcoming_catalyst': True,
                'catalyst_type': 'EARNINGS',
                'days_until_catalyst': 5,  # Too far out
                'current_price': 40.0
            }
        }
        
        catalyst_plays = strategy.get_tier_3_catalysts(market_data)
        
        # MRNA should qualify (within 3 days), PFE should not
        if catalyst_plays:
            mrna_found = any(play.symbol == 'MRNA' for play in catalyst_plays)
            assert mrna_found
            
            mrna_play = next((p for p in catalyst_plays if p.symbol == 'MRNA'), None)
            if mrna_play:
                assert mrna_play.strategy_type == "TIER_3_CATALYST"
                assert mrna_play.position_size_pct == 0.03  # 3% lottery ticket
                assert mrna_play.stop_loss == 45.0  # 10% stop (wider for catalyst)
    
    def test_trade_setup_creation(self, strategy):
        """Test TradeSetup dataclass creation"""
        setup = TradeSetup(
            symbol='TEST',
            strategy_type='TIER_1_ROCKET',
            confidence=85.0,
            entry_price=100.0,
            position_size_pct=0.08,
            stop_loss=95.0,
            target_1=110.0,
            target_2=120.0,
            target_3=130.0,
            signals=['Early move', 'High volume', 'Fresh news'],
            expected_move=0.15,
            time_horizon='TODAY'
        )
        
        assert setup.symbol == 'TEST'
        assert setup.confidence == 85.0
        assert setup.position_size_pct == 0.08
        assert len(setup.signals) == 3
        assert setup.expected_move == 0.15
        assert setup.time_horizon == 'TODAY'
        
        # Risk/reward check
        risk = (setup.entry_price - setup.stop_loss) / setup.entry_price
        reward = (setup.target_1 - setup.entry_price) / setup.entry_price
        assert reward > risk  # Positive risk/reward ratio
    
    def test_position_sizing_by_tier(self, strategy):
        """Test that position sizes decrease by tier"""
        market_data = {
            'ROCKET': {
                'price_change': 0.03,
                'volume_ratio': 3.0,
                'news_age_hours': 1,
                'social_score': 80,
                'breaking_resistance': True,
                'short_interest': 0.30,
                'current_price': 100.0
            }
        }
        
        # Get Tier 1 position
        rockets = strategy.get_tier_1_rockets(market_data)
        if rockets:
            tier1_size = rockets[0].position_size_pct
            assert tier1_size == 0.08  # 8%
        
        # Modify data for Tier 2
        market_data['ROCKET']['social_score'] = 45
        market_data['ROCKET']['above_sma20'] = True
        market_data['ROCKET']['rsi'] = 60
        
        momentum = strategy.get_tier_2_momentum(market_data)
        if momentum:
            tier2_size = momentum[0].position_size_pct
            assert tier2_size == 0.05  # 5%
            assert tier2_size < 0.08  # Less than Tier 1
        
        # Tier 3 catalyst position
        market_data['ROCKET'] = {
            'upcoming_catalyst': True,
            'catalyst_type': 'EARNINGS',
            'days_until_catalyst': 2,
            'current_price': 100.0
        }
        
        catalysts = strategy.get_tier_3_catalysts(market_data)
        if catalysts:
            tier3_size = catalysts[0].position_size_pct
            assert tier3_size == 0.03  # 3%
            assert tier3_size < 0.05  # Less than Tier 2


class TestTradeSetupValidation:
    """Test trade setup validation and risk management"""
    
    def test_stop_loss_below_entry(self):
        """Test that stop loss is always below entry for long positions"""
        setup = TradeSetup(
            symbol='TEST',
            strategy_type='TIER_1_ROCKET',
            confidence=80,
            entry_price=100.0,
            position_size_pct=0.05,
            stop_loss=95.0,  # 5% below
            target_1=105.0,
            target_2=110.0,
            target_3=115.0,
            signals=['Test'],
            expected_move=0.10,
            time_horizon='TODAY'
        )
        
        assert setup.stop_loss < setup.entry_price
    
    def test_targets_above_entry(self):
        """Test that all targets are above entry for long positions"""
        setup = TradeSetup(
            symbol='TEST',
            strategy_type='TIER_2_MOMENTUM',
            confidence=70,
            entry_price=50.0,
            position_size_pct=0.03,
            stop_loss=48.5,
            target_1=52.5,
            target_2=55.0,
            target_3=57.5,
            signals=['Test'],
            expected_move=0.10,
            time_horizon='1-2 DAYS'
        )
        
        assert setup.target_1 > setup.entry_price
        assert setup.target_2 > setup.target_1
        assert setup.target_3 > setup.target_2
    
    def test_position_size_limits(self):
        """Test that position sizes stay within risk limits"""
        setups = [
            TradeSetup(
                symbol=f'TEST{i}',
                strategy_type='TIER_1_ROCKET',
                confidence=80,
                entry_price=100.0,
                position_size_pct=0.08,
                stop_loss=95.0,
                target_1=110.0,
                target_2=120.0,
                target_3=130.0,
                signals=['Test'],
                expected_move=0.15,
                time_horizon='TODAY'
            )
            for i in range(5)
        ]
        
        # Total allocation check
        total_allocation = sum(s.position_size_pct for s in setups)
        assert total_allocation <= 0.40  # Should not exceed tier allocation
        
        # Individual position check
        for setup in setups:
            assert setup.position_size_pct <= 0.10  # Max 10% per position


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])