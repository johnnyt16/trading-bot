#!/usr/bin/env python3
"""
Tests for Social Sentiment Scanner
Testing StockTwits and Reddit sentiment analysis
"""

import sys
import os
import pytest
from unittest.mock import Mock, MagicMock, patch
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.strategies.social_sentiment_scanner import SocialSentimentScanner, SocialIntegration


class TestSocialSentimentScanner:
    """Test social sentiment scanning functionality"""
    
    @pytest.fixture
    def scanner(self):
        """Create scanner instance"""
        return SocialSentimentScanner()
    
    def test_scanner_initialization(self, scanner):
        """Test scanner initializes correctly"""
        assert scanner.stocktwits_base == "https://api.stocktwits.com/api/2"
        assert scanner.wsb_url == "https://www.reddit.com/r/wallstreetbets"
        assert scanner.trending_tickers == {}
    
    @patch('requests.get')
    def test_stocktwits_sentiment_analysis(self, mock_get, scanner):
        """Test StockTwits sentiment extraction"""
        # Mock StockTwits API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'messages': [
                {
                    'created_at': '2024-01-15T10:00:00Z',
                    'entities': {
                        'sentiment': {'basic': 'Bullish'}
                    }
                },
                {
                    'created_at': '2024-01-15T09:30:00Z',
                    'entities': {
                        'sentiment': {'basic': 'Bullish'}
                    }
                },
                {
                    'created_at': '2024-01-15T09:00:00Z',
                    'entities': {
                        'sentiment': {'basic': 'Bearish'}
                    }
                }
            ]
        }
        mock_get.return_value = mock_response
        
        result = scanner.get_stocktwits_sentiment('TSLA')
        
        assert result['sentiment_score'] > 0.5  # More bullish than bearish
        assert result['bullish_pct'] > result['bearish_pct']
        assert result['message_volume'] == 3
        assert 'signal' in result
    
    @patch('requests.get')
    def test_wsb_ticker_extraction(self, mock_get, scanner):
        """Test Reddit WSB ticker extraction"""
        # Mock Reddit API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': {
                'children': [
                    {
                        'data': {
                            'title': 'Daily Discussion Thread',
                            'id': 'test123'
                        }
                    }
                ]
            }
        }
        
        # Mock comments response
        mock_comments = MagicMock()
        mock_comments.status_code = 200
        mock_comments.json.return_value = [
            {},  # First element is post data
            {
                'data': {
                    'children': [
                        {
                            'data': {
                                'body': 'I think $TSLA is going to moon! TSLA calls all day.',
                                'replies': ''
                            }
                        },
                        {
                            'data': {
                                'body': '$GME is the play. GME GME GME!',
                                'replies': ''
                            }
                        },
                        {
                            'data': {
                                'body': 'NVDA looking good today',
                                'replies': ''
                            }
                        }
                    ]
                }
            }
        ]
        
        mock_get.side_effect = [mock_response, mock_comments]
        
        result = scanner.scan_wsb_daily_thread()
        
        # Should find tickers mentioned
        assert len(result) > 0
        if 'TSLA' in result:
            assert result['TSLA']['mentions'] >= 2  # Mentioned twice
        if 'GME' in result:
            assert result['GME']['mentions'] >= 3  # Mentioned three times
    
    def test_sentiment_interpretation(self, scanner):
        """Test sentiment signal interpretation"""
        # Test strong bullish signal
        signal = scanner._interpret_sentiment(0.85, 40)
        assert signal == "STRONG_BUY"
        
        # Test moderate bullish signal
        signal = scanner._interpret_sentiment(0.70, 25)
        assert signal == "BUY"
        
        # Test bearish signal
        signal = scanner._interpret_sentiment(0.25, 25)
        assert signal == "SELL"
        
        # Test high attention but neutral sentiment
        signal = scanner._interpret_sentiment(0.50, 60)
        assert signal == "HIGH_ATTENTION"
        
        # Test low activity
        signal = scanner._interpret_sentiment(0.50, 10)
        assert signal == "NEUTRAL"
    
    def test_wsb_mention_interpretation(self, scanner):
        """Test WSB mention count interpretation"""
        # Test meme stock frenzy
        signal = scanner._interpret_wsb_mentions(150)
        assert signal == "WSB_FRENZY"
        
        # Test trending
        signal = scanner._interpret_wsb_mentions(75)
        assert signal == "WSB_TRENDING"
        
        # Test mentioned
        signal = scanner._interpret_wsb_mentions(30)
        assert signal == "WSB_MENTIONED"
        
        # Test low buzz
        signal = scanner._interpret_wsb_mentions(10)
        assert signal == "LOW_BUZZ"
    
    @patch.object(SocialSentimentScanner, 'get_stocktwits_sentiment')
    @patch.object(SocialSentimentScanner, 'scan_wsb_daily_thread')
    def test_combined_social_score(self, mock_wsb, mock_stocktwits, scanner):
        """Test combined social scoring"""
        # Mock StockTwits data
        mock_stocktwits.return_value = {
            'sentiment_score': 0.75,
            'bullish_pct': 75,
            'is_trending': True,
            'messages_per_hour': 25,
            'message_volume': 100
        }
        
        # Mock WSB data
        mock_wsb.return_value = {
            'TSLA': {'mentions': 60, 'signal': 'WSB_TRENDING'}
        }
        
        result = scanner.get_social_score('TSLA')
        
        assert result['symbol'] == 'TSLA'
        assert result['social_score'] > 60  # High social score
        assert result['action'] == "BUY_SOCIAL_MOMENTUM"
        assert len(result['signals']) > 0


class TestSocialIntegration:
    """Test social sentiment integration helper"""
    
    @pytest.fixture
    def integration(self):
        """Create integration instance"""
        return SocialIntegration()
    
    @patch.object(SocialSentimentScanner, 'get_social_score')
    def test_signal_enhancement(self, mock_get_score, integration):
        """Test enhancing existing signals with social data"""
        # Mock social score
        mock_get_score.return_value = {
            'symbol': 'TSLA',
            'social_score': 75,
            'action': 'BUY_SOCIAL_MOMENTUM',
            'stocktwits_sentiment': 0.8,
            'wsb_mentions': 100,
            'signals': ['StockTwits 80% bullish', 'WSB 100 mentions']
        }
        
        # Enhance an existing signal
        result = integration.enhance_signal_with_social('TSLA', 50.0)
        
        assert result['original_score'] == 50.0
        assert result['social_boost'] == 25  # Added boost
        assert result['final_score'] == 75.0  # Enhanced score
        assert result['social_data']['symbol'] == 'TSLA'
    
    @patch.object(SocialSentimentScanner, 'get_social_score')
    def test_moderate_social_boost(self, mock_get_score, integration):
        """Test moderate social sentiment boost"""
        mock_get_score.return_value = {
            'symbol': 'AAPL',
            'social_score': 45,
            'action': 'WATCH_BUILDING',
            'stocktwits_sentiment': 0.6,
            'wsb_mentions': 25,
            'signals': ['Building momentum']
        }
        
        result = integration.enhance_signal_with_social('AAPL', 60.0)
        
        assert result['original_score'] == 60.0
        assert result['social_boost'] == 10  # Moderate boost
        assert result['final_score'] == 70.0
    
    @patch.object(SocialSentimentScanner, 'get_social_score')
    def test_no_social_boost(self, mock_get_score, integration):
        """Test no boost when social signal is weak"""
        mock_get_score.return_value = {
            'symbol': 'MSFT',
            'social_score': 20,
            'action': 'NO_SOCIAL_SIGNAL',
            'stocktwits_sentiment': 0.5,
            'wsb_mentions': 5,
            'signals': []
        }
        
        result = integration.enhance_signal_with_social('MSFT', 40.0)
        
        assert result['original_score'] == 40.0
        assert result['social_boost'] == 0  # No boost
        assert result['final_score'] == 40.0


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])