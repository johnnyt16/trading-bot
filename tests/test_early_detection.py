#!/usr/bin/env python3
"""
Tests for Early Detection Scanner
Testing the core functionality of catching moves at 0.5-3%
"""

import sys
import os
import pytest
import asyncio
from datetime import datetime, time, timedelta
from unittest.mock import Mock, MagicMock, patch
import pytz

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.strategies.early_detection_scanner import OptimizedEarlyDetectionScanner, EarlyDetectionIntegration


class TestEarlyDetectionScanner:
    """Test the early detection scanner functionality"""
    
    @pytest.fixture
    def mock_api(self):
        """Create a mock Alpaca API client"""
        api = MagicMock()
        return api
    
    @pytest.fixture
    def scanner(self, mock_api):
        """Create scanner instance with mock API"""
        return OptimizedEarlyDetectionScanner(mock_api)
    
    def test_scanner_initialization(self, scanner):
        """Test scanner initializes with correct thresholds"""
        assert scanner.early_thresholds['pre_market']['min_move'] == 0.005  # 0.5%
        assert scanner.early_thresholds['pre_market']['max_move'] == 0.03   # 3%
        assert scanner.early_thresholds['market_hours']['min_move'] == 0.01  # 1%
        assert scanner.early_thresholds['market_hours']['max_move'] == 0.04  # 4%
    
    def test_market_session_detection(self, scanner):
        """Test correct market session identification"""
        eastern = pytz.timezone('US/Eastern')
        
        # Mock different times
        with patch('src.strategies.early_detection_scanner.datetime') as mock_dt:
            # Pre-market test (7:30 AM EST)
            mock_dt.now.return_value = eastern.localize(
                datetime(2024, 1, 15, 7, 30, 0)
            )
            session, _ = scanner.get_market_session()
            assert session == 'earnings_window'
            
            # Market open test (9:45 AM EST)
            mock_dt.now.return_value = eastern.localize(
                datetime(2024, 1, 15, 9, 45, 0)
            )
            session, minutes = scanner.get_market_session()
            assert session == 'opening_momentum'
            assert minutes == 15  # 15 minutes since open
            
            # Regular hours test (2 PM EST)
            mock_dt.now.return_value = eastern.localize(
                datetime(2024, 1, 15, 14, 0, 0)
            )
            session, _ = scanner.get_market_session()
            assert session == 'regular_hours'
    
    @pytest.mark.asyncio
    async def test_early_movement_detection(self, scanner, mock_api):
        """Test detection of early stock movements"""
        # Create mock snapshot data
        mock_snapshot = MagicMock()
        mock_snapshot.minute_bar.c = 102.0  # Current price
        mock_snapshot.minute_bar.v = 50000  # Current volume
        mock_snapshot.prev_daily_bar.c = 100.0  # Previous close
        mock_snapshot.prev_daily_bar.v = 1000000  # Previous day volume
        
        mock_api.get_snapshot.return_value = mock_snapshot
        
        # Mock bars for move start detection
        mock_bars = MagicMock()
        mock_bars.df = MagicMock()
        mock_api.get_bars.return_value = mock_bars
        
        # Test with 2% move (should be detected as early)
        thresholds = scanner.early_thresholds['market_hours']
        result = await scanner._check_early_movement('TEST', thresholds, 'market_hours')
        
        # 2% move is within early range (1-4%)
        assert result['symbol'] == 'TEST'
        if result['is_early']:
            assert 0.01 <= abs(result['price_change']) <= 0.04
    
    @pytest.mark.asyncio
    async def test_volume_acceleration_check(self, scanner, mock_api):
        """Test volume acceleration detection"""
        import pandas as pd
        import numpy as np
        
        # Create mock bars with increasing volume
        mock_bars = MagicMock()
        mock_bars.df = pd.DataFrame({
            'volume': [1000, 2000, 3000, 4000, 5000]  # Increasing volume
        })
        mock_api.get_bars.return_value = mock_bars
        
        result = await scanner._check_volume_acceleration('TEST')
        assert result == True  # Should detect acceleration
        
        # Test with decreasing volume
        mock_bars.df = pd.DataFrame({
            'volume': [5000, 4000, 3000, 2000, 1000]  # Decreasing volume
        })
        mock_api.get_bars.return_value = mock_bars
        
        result = await scanner._check_volume_acceleration('TEST')
        assert result == False  # Should not detect acceleration
    
    @pytest.mark.asyncio
    async def test_catalyst_detection(self, scanner, mock_api):
        """Test news catalyst detection"""
        # Create mock news
        mock_news = [MagicMock()]
        mock_news[0].created_at = datetime.now(pytz.UTC) - timedelta(hours=1)
        mock_news[0].headline = "Company beats earnings expectations"
        
        mock_api.get_news.return_value = mock_news
        
        result = await scanner._check_recent_catalyst('TEST')
        assert result['has_catalyst'] == True
        assert result['catalyst_type'] == 'earnings'
    
    def test_continuation_estimation(self, scanner):
        """Test expected move continuation calculation"""
        # Test with 2% current move, high volume
        continuation = scanner._estimate_continuation(0.02, 3.0, 'opening_momentum')
        
        # Should expect reasonable continuation
        assert continuation > 0.02  # More than current move
        assert continuation <= 0.20  # But capped at 20%


class TestEarlyDetectionIntegration:
    """Test the integration helper class"""
    
    @pytest.fixture
    def integration(self):
        """Create integration instance"""
        mock_api = MagicMock()
        return EarlyDetectionIntegration(mock_api)
    
    @pytest.mark.asyncio
    async def test_entry_decision(self, integration):
        """Test position entry decision logic"""
        # Test with move too late (35 minutes old)
        data = {
            'minutes_since_start': 35,
            'price_change': 0.02,
            'opportunity_score': 80
        }
        should_enter = await integration.should_enter_position('TEST', data)
        assert should_enter == False  # Too late
        
        # Test with move too extended (6%)
        data = {
            'minutes_since_start': 10,
            'price_change': 0.06,
            'opportunity_score': 80
        }
        should_enter = await integration.should_enter_position('TEST', data)
        assert should_enter == False  # Too extended
        
        # Test with perfect early setup
        data = {
            'minutes_since_start': 5,
            'price_change': 0.015,  # 1.5%
            'opportunity_score': 75
        }
        should_enter = await integration.should_enter_position('TEST', data)
        assert should_enter == True  # Perfect early entry
    
    @pytest.mark.asyncio
    async def test_position_sizing(self, integration):
        """Test dynamic position sizing based on earliness"""
        # Very early (3 minutes)
        data = {'minutes_since_start': 3}
        size = await integration.get_position_size(data)
        assert size == 0.08  # 8% position
        
        # Early (10 minutes)
        data = {'minutes_since_start': 10}
        size = await integration.get_position_size(data)
        assert size == 0.05  # 5% position
        
        # Getting late (25 minutes)
        data = {'minutes_since_start': 25}
        size = await integration.get_position_size(data)
        assert size == 0.03  # 3% position
        
        # Too late (40 minutes)
        data = {'minutes_since_start': 40}
        size = await integration.get_position_size(data)
        assert size == 0.02  # Minimal 2% position


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])