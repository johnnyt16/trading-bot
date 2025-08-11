#!/usr/bin/env python3
"""
gpt5_trading_system.py - Ultimate AI-first trading system using GPT-5
Designed for OpenAI's most advanced model with web search and reasoning
"""

import os
import logging
import asyncio
import json
import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import deque
import openai
from openai import AsyncOpenAI
import alpaca_trade_api as tradeapi
from loguru import logger
import pandas as pd
import numpy as np
from tavily import TavilyClient  # Web search API
import yfinance as yf  # Keep for fundamental research
from dotenv import load_dotenv
import pytz
from src.utils.market_data import fetch_finnhub_profile, fetch_yf_snapshot, fetch_yf_options_summary
def categorize_symbol_advanced(symbol: str, price: float, volume: float, additional_data: Optional[Dict] = None) -> Tuple[str, float]:
    """Multi-factor categorization with confidence scoring."""
    aggressive_score = 0
    conservative_score = 0

    # Price factors
    if price < 5:
        aggressive_score += 3
    elif price < 10:
        aggressive_score += 2
    elif price > 50:
        conservative_score += 2

    # Volume/liquidity factors
    if volume > 10_000_000:
        aggressive_score += 1
    elif volume > 0 and volume < 500_000:
        aggressive_score += 2

    # Additional factors
    if additional_data:
        if additional_data.get('short_interest_pct', 0) > 30:
            aggressive_score += 3
        if additional_data.get('unusual_options_activity'):
            aggressive_score += 2
        market_cap = additional_data.get('market_cap', float('inf'))
        if market_cap < 300_000_000:
            aggressive_score += 3
        elif market_cap > 10_000_000_000:
            conservative_score += 3
        beta = additional_data.get('beta', 1.0)
        if beta > 2:
            aggressive_score += 2
        elif beta < 0.8:
            conservative_score += 2
        catalyst = str(additional_data.get('catalyst_type', '')).lower()
        if catalyst in ['fda_approval', 'short_squeeze', 'bankruptcy_emergence']:
            aggressive_score += 3
        elif catalyst in ['earnings', 'dividend', 'guidance']:
            conservative_score += 1

    total = aggressive_score + conservative_score
    confidence = abs(aggressive_score - conservative_score) / (total or 1)
    return ('aggressive', confidence) if aggressive_score > conservative_score else ('conservative', confidence)


class DynamicAllocationManager:
    def __init__(self, base_safe_pct: float = 0.6, base_aggressive_pct: float = 0.4):
        self.base_safe = base_safe_pct
        self.base_aggressive = base_aggressive_pct
        self.performance_window: deque = deque(maxlen=20)

    def record_trade(self, category: str, pnl: float) -> None:
        self.performance_window.append({'category': category, 'pnl': pnl})

    def adjust_allocations(self, market_conditions: Dict) -> Tuple[float, float]:
        aggressive_trades = [t for t in self.performance_window if t['category'] == 'aggressive']
        wins = [t for t in aggressive_trades if t['pnl'] > 0]
        agg_win_rate = (len(wins) / len(aggressive_trades)) if aggressive_trades else 0
        vix = market_conditions.get('vix', 20)
        # Basic regime logic
        if agg_win_rate > 0.6 and vix < 25:
            aggressive_pct = min(self.base_aggressive + 0.1, 0.5)
        elif agg_win_rate < 0.3 or vix > 30:
            aggressive_pct = max(self.base_aggressive - 0.15, 0.2)
        else:
            aggressive_pct = self.base_aggressive
        safe_pct = 1 - aggressive_pct
        return safe_pct, aggressive_pct


class DualBucketPerformanceTracker:
    def __init__(self):
        self.metrics: Dict[str, Dict] = {
            'conservative': {'total_trades': 0, 'wins': 0, 'total_pnl': 0.0, 'best_trade': 0.0, 'worst_trade': 0.0, 'avg_win': 0.0, 'avg_loss': 0.0},
            'aggressive': {'total_trades': 0, 'wins': 0, 'total_pnl': 0.0, 'best_trade': 0.0, 'worst_trade': 0.0, 'avg_win': 0.0, 'avg_loss': 0.0, 'home_runs': 0}
        }

    def update_metrics(self, category: str, pnl_pct: float) -> None:
        m = self.metrics[category]
        m['total_trades'] += 1
        m['total_pnl'] += pnl_pct
        m['best_trade'] = max(m['best_trade'], pnl_pct)
        m['worst_trade'] = min(m['worst_trade'], pnl_pct)
        if pnl_pct > 0:
            m['wins'] += 1
            if category == 'aggressive' and pnl_pct >= 400.0:
                m['home_runs'] += 1

load_dotenv()

# Reduce noisy logs from third-party libs (e.g., yfinance weekend errors)
logging.getLogger('yfinance').setLevel(logging.ERROR)
logging.getLogger('yfinance.ticker').setLevel(logging.ERROR)
logging.getLogger('urllib3').setLevel(logging.WARNING)

class GPT5TradingBrain:
    """
    The most advanced AI trading system using GPT-5
    Complete autonomous trading with web search and reasoning
    """
    
    def __init__(self):
        # Initialize OpenAI client
        self.client = AsyncOpenAI(
            api_key=os.getenv('OPENAI_API_KEY')
        )

        # Cost mode and cadence controls
        self.cost_mode = os.getenv('COST_MODE', 'low').lower()  # low | medium | high
        # Scan cadence and limits (env overrideable)
        self.scan_min_interval_seconds = int(os.getenv('SCAN_MIN_INTERVAL_SECONDS', '300'))  # 5m default
        self.deep_analysis_min_interval_seconds = int(os.getenv('DEEP_ANALYSIS_MIN_INTERVAL_SECONDS', '900'))  # 15m default
        self.position_management_min_interval_seconds = int(os.getenv('POSITION_MANAGEMENT_MIN_INTERVAL_SECONDS', '600'))  # 10m
        self.max_gpt_requests_per_hour = int(os.getenv('MAX_GPT_REQUESTS_PER_HOUR', '30'))
        # Token cap by mode
        if self.cost_mode == 'low':
            self.model_hierarchy = [
                "gpt-4o-mini",
                "gpt-3.5-turbo",
                "gpt-4o",
                "gpt-4-turbo",
            ]
            self.max_tokens_cap = int(os.getenv('MAX_TOKENS_CAP', '700'))
        elif self.cost_mode == 'medium':
            self.model_hierarchy = [
                "gpt-4o-mini",
                "gpt-4o",
                "gpt-4-turbo",
            ]
            self.max_tokens_cap = int(os.getenv('MAX_TOKENS_CAP', '1200'))
        else:  # high
            self.model_hierarchy = [
                "gpt-4o",
                "gpt-4-turbo",
                "gpt-4o-mini",
            ]
            self.max_tokens_cap = int(os.getenv('MAX_TOKENS_CAP', '2000'))

        # Start with the first model for the selected mode
        self.current_model_index = 0
        self.model = self.model_hierarchy[self.current_model_index]
        
        # Track rate limit issues
        self.rate_limit_errors = 0
        self.last_rate_limit_time = None
        
        # Web search capability with rate limiting
        self.tavily = TavilyClient(api_key=os.getenv('TAVILY_API_KEY'))
        self._tavily_request_times = deque()  # Track request times for rate limiting
        self._tavily_rate_limit = 4.5  # 4.5 requests per second (slightly under 5 to be safe)
        self._tavily_fallback_mode = False  # Enable fallback mode when API is unavailable
        
        # Cost-aware Tavily controls
        # Default to 40/day per user budget; override via env if needed
        self.tavily_daily_credit_budget = int(os.getenv('TAVILY_DAILY_CREDIT_BUDGET', '40'))
        self.tavily_weekly_credit_budget = int(os.getenv('TAVILY_WEEKLY_CREDIT_BUDGET', '200'))
        self.tavily_max_results = int(os.getenv('TAVILY_MAX_RESULTS', '2'))
        self.tavily_symbol_cooldown_minutes = int(os.getenv('TAVILY_SYMBOL_COOLDOWN_MINUTES', '120'))
        include_domains_env = os.getenv('TAVILY_INCLUDE_DOMAINS', '')
        if include_domains_env.strip():
            self.tavily_include_domains = [d.strip() for d in include_domains_env.split(',') if d.strip()]
        else:
            self.tavily_include_domains = [
                "reuters.com", "bloomberg.com", "cnbc.com", "marketwatch.com", "seekingalpha.com"
            ]
        # Daily/weekly usage accounting
        self._tavily_credits_today: int = 0
        self._tavily_last_reset_date = datetime.now().date()
        self._tavily_credits_this_week: int = 0
        today = datetime.now().date()
        self._tavily_week_start_date = today - timedelta(days=today.weekday())
        self._tavily_last_search_for_symbol: Dict[str, datetime] = {}
        # Credit buckets (premarket/intraday/buffer)
        self._init_tavily_buckets()

        # Confidence scoring thresholds
        self.pre_gpt_min_score = int(os.getenv('PRE_GPT_MIN_SCORE', '60'))
        # Independent of risk_limits to avoid init order dependency
        self.min_confidence_score = int(os.getenv('MIN_CONFIDENCE_SCORE', '60'))

        # Earnings calendar cache (optional file at data/earnings_calendar.csv)
        self._earnings_by_date: Dict[str, List[str]] = {}
        self._load_earnings_calendar()

        # Portfolio allocation between conservative and aggressive plays
        self.safe_allocation_pct = float(os.getenv('SAFE_ALLOCATION_PCT', '0.6'))
        self.aggressive_allocation_pct = float(os.getenv('AGGRESSIVE_ALLOCATION_PCT', '0.4'))
        if self.safe_allocation_pct + self.aggressive_allocation_pct > 1.0:
            # Normalize if user misconfigured
            total = self.safe_allocation_pct + self.aggressive_allocation_pct
            self.safe_allocation_pct /= total
            self.aggressive_allocation_pct /= total
        # Track category of executed positions (symbol -> 'conservative'|'aggressive')
        self._category_by_symbol: Dict[str, str] = {}

        # Dynamic allocation manager & performance tracker
        self._allocation_manager = DynamicAllocationManager(
            base_safe_pct=self.safe_allocation_pct,
            base_aggressive_pct=self.aggressive_allocation_pct,
        )
        self._performance_tracker = DualBucketPerformanceTracker()
        
        # Alpaca for execution
        self.alpaca = tradeapi.REST(
            os.getenv('ALPACA_API_KEY'),
            os.getenv('ALPACA_SECRET_KEY'),
            os.getenv('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets')
        )
        
        # Risk parameters (AI can override within limits)
        self.risk_limits = {
            'max_position_pct': 0.20,    # 20% max per position
            'max_daily_loss_pct': 0.15,  # 15% daily loss limit
            'max_positions': 10,         # 10 concurrent positions
            'min_confidence': 60         # Minimum AI confidence as integer percent
        }

        # Optional environment overrides for risk configuration
        try:
            max_pos_env = os.getenv('MAX_POSITION_SIZE')
            if max_pos_env is not None:
                self.risk_limits['max_position_pct'] = float(max_pos_env)

            max_daily_env = os.getenv('MAX_DAILY_LOSS_PERCENT')
            if max_daily_env is not None:
                # Accept 0-1 (e.g., 0.15) or 0-100 (e.g., 15) → always store as 0-1
                val = float(max_daily_env)
                self.risk_limits['max_daily_loss_pct'] = val / 100.0 if val > 1 else val

            min_conf_env = os.getenv('MIN_CONFIDENCE_SCORE')
            if min_conf_env is not None:
                # Accept 0-1 or 0-100 → store as integer percent
                val = float(min_conf_env)
                self.risk_limits['min_confidence'] = int(val * 100) if val <= 1 else int(val)
        except Exception as _:
            # If parsing fails, keep defaults
            pass
        
        # Simple budget tracking for GPT calls (rolling 1h window)
        self._gpt_call_times: deque = deque()

        # Caches and cooldowns to avoid repeated GPT work
        self._last_market_scan_at: Optional[datetime] = None
        self._last_market_scan_result: List[Dict] = []
        self._last_analysis_by_symbol: Dict[str, Dict] = {}
        self._last_position_management_at: Optional[datetime] = None

        # Track AI's performance and learning
        self.ai_memory = []
        self.successful_patterns = []
        
        # The Master Prompt - This defines the AI's trading personality
        self.system_prompt = """
        You are an ELITE AI Trading System designed for MAXIMUM RETURNS. Your sole purpose is to generate exceptional profits through intelligent, data-driven trading.
        
        🎯 PRIMARY OBJECTIVE: Turn $1,000 into $10,000+ in 3 months
        
        CORE TRADING PHILOSOPHY:
        1. EARLY DETECTION: Identify opportunities 30-60 minutes before the crowd
        2. CATALYST-DRIVEN: Only trade with clear, powerful catalysts
        3. MOMENTUM MASTERY: Enter at the beginning of moves, not the middle
        4. RISK/REWARD DISCIPLINE: Never take trades with less than 1:3 risk/reward
        5. POSITION SIZING: Scale aggressively on high-conviction plays (up to 20% per position)
        
        HIGH-PRIORITY OPPORTUNITIES (FOCUS HERE):
        • FDA Approvals: Biotech/pharma with PDUFA dates or trial results
        • Earnings Surprises: Companies beating by >20% with raised guidance  
        • Short Squeezes: High short interest (>25%) with positive catalyst
        • M&A Activity: Takeover targets or acquisition announcements
        • Analyst Upgrades: Major bank upgrades with >20% price target increases
        • Volume Breakouts: Stocks with 5x+ normal volume in first hour
        • Sector Rotation: Money flowing into hot sectors (AI, quantum, biotech)
        • Pre-market Movers: Stocks up 3-7% pre-market on news (not too extended)
        
        WINNING PATTERNS TO EXPLOIT:
        • Morning Panic Sells → Reversal trades at 9:45-10:15 AM
        • Lunchtime Breakouts → 12:00-1:00 PM when algos are quiet
        • Power Hour Momentum → 3:00-4:00 PM institutional buying
        • Gap & Go → Stocks gapping up 2-5% on volume
        • News Catalyst + Technical Setup → Double confirmation trades
        
        STRICT RULES FOR SUCCESS:
        ✅ ALWAYS enter with a plan: Entry, Stop, 3 Targets
        ✅ ALWAYS use stops: Maximum 3-5% loss per trade
        ✅ ALWAYS respect position sizing: Max 20% on highest conviction
        ✅ NEVER chase: If you missed the entry by >1%, find another trade
        ✅ NEVER hold losers: Cut at stop, no "hoping"
        ✅ ALWAYS compound: Reinvest profits into next opportunities
        
        PSYCHOLOGICAL EDGE:
        - You have no fear, greed, or ego
        - You process information 1000x faster than humans
        - You can analyze 100 stocks while humans look at 1
        - You never get tired, emotional, or biased
        - You learn from every trade and improve continuously
        
        PROFIT TARGETS:
        • Day Trades: 5-15% gains (hold 1-6 hours)
        • Swing Trades: 10-30% gains (hold 1-5 days) 
        • Runners: 30-100% gains (hold with trailing stop)
        
        Remember: The market rewards the prepared, the disciplined, and the fast.
        You are all three. Now find opportunities that others haven't discovered yet.
        Every trade should have EXPLOSIVE potential with LIMITED downside.
        """
        
        logger.info(f"GPT-5 Trading Brain initialized - Using model: {self.model}")
        logger.info("Autonomous mode activated with automatic model fallback")
        logger.info(f"Cost mode: {self.cost_mode} | max_tokens_cap: {self.max_tokens_cap} | max_gpt_requests_per_hour: {self.max_gpt_requests_per_hour}")
        logger.info(f"Cadence: scan>={self.scan_min_interval_seconds}s, deep_analysis>={self.deep_analysis_min_interval_seconds}s, manage_positions>={self.position_management_min_interval_seconds}s")
    
    async def _safe_tavily_search(self, query: str, max_results: int = 3, max_retries: int = 3, **kwargs) -> Dict:
        """
        Rate-limited and error-handled Tavily search with exponential backoff retry
        """
        # If in fallback mode due to usage limits, return empty results immediately
        if self._tavily_fallback_mode:
            logger.debug("Tavily in fallback mode (usage limit exceeded), skipping search")
            return {'results': [], 'error': 'fallback_mode'}

        # Reset daily/weekly counters at midnight and weekly on Monday
        today = datetime.now().date()
        if self._tavily_last_reset_date != today:
            self._tavily_last_reset_date = today
            self._tavily_credits_today = 0
            self._tavily_last_search_for_symbol = {}
        # Weekly reset (Monday)
        try:
            current_week_start = today - timedelta(days=today.weekday())
            if getattr(self, '_tavily_week_start_date', current_week_start) != current_week_start:
                self._tavily_week_start_date = current_week_start
                self._tavily_credits_this_week = 0
        except Exception:
            pass

        # Enforce daily and weekly credit budgets
        if (
            self._tavily_credits_today >= self.tavily_daily_credit_budget
            or getattr(self, '_tavily_credits_this_week', 0) >= getattr(self, 'tavily_weekly_credit_budget', 10**9)
            or not self._check_tavily_bucket_allowance()
        ): 
            logger.info("Tavily credit budget reached (daily/weekly), skipping search")
            return {'results': [], 'error': 'daily_budget_exhausted'}

        # Per-symbol cooldown (if symbol present in query)
        symbol_in_query = None
        try:
            # Very simple heuristic: uppercase token of 1-5 letters
            for token in query.split():
                t = ''.join([c for c in token if c.isalpha()])
                if 1 <= len(t) <= 5 and t.isupper():
                    symbol_in_query = t
                    break
        except Exception:
            pass

        if symbol_in_query:
            last = self._tavily_last_search_for_symbol.get(symbol_in_query)
            if last and (datetime.now() - last).total_seconds() < self.tavily_symbol_cooldown_minutes * 60:
                logger.debug(f"Cooldown active for {symbol_in_query}, skipping Tavily search")
                return {'results': [], 'error': 'symbol_cooldown'}
        
        if len(query) > 400:
            logger.warning(f"Query too long ({len(query)} chars), truncating to 400 chars")
            query = query[:400]
        
        # Rate limiting: ensure we don't exceed 4.5 requests per second
        now = time.time()
        
        # Remove requests older than 1 second
        while self._tavily_request_times and now - self._tavily_request_times[0] > 1.0:
            self._tavily_request_times.popleft()
        
        # If we have 4+ requests in the last second, wait
        if len(self._tavily_request_times) >= int(self._tavily_rate_limit):
            wait_time = 1.0 - (now - self._tavily_request_times[0]) + 0.1  # Add small buffer
            if wait_time > 0:
                logger.debug(f"Rate limiting: waiting {wait_time:.2f}s before Tavily request")
                await asyncio.sleep(wait_time)
        
        # Record this request time
        self._tavily_request_times.append(time.time())
        
        # Attempt the search with retries (fewer in low-cost mode)
        effective_max_retries = 1 if self.cost_mode == 'low' else min(max_retries, 2)
        for attempt in range(effective_max_retries):
            try:
                logger.debug(f"Tavily search (attempt {attempt + 1}): {query[:50]}...")
                
                # Make the API call with timeout
                result = await asyncio.wait_for(
                    asyncio.to_thread(
                        self.tavily.search,
                        query,
                        max_results=max_results,
                        **kwargs
                    ),
                    timeout=30.0  # 30 second timeout
                )
                
                logger.debug(f"Tavily search successful, got {len(result.get('results', []))} results")
                # Account for credits: basic search = 1 credit
                self._tavily_credits_today += 1
                try:
                    self._tavily_credits_this_week += 1
                except Exception:
                    pass
                self._consume_tavily_bucket_credit()
                if symbol_in_query:
                    self._tavily_last_search_for_symbol[symbol_in_query] = datetime.now()
                return result
                
            except asyncio.TimeoutError:
                logger.warning(f"Tavily search timeout (attempt {attempt + 1})")
                if attempt == max_retries - 1:
                    return {'results': [], 'error': 'timeout'}
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                
            except Exception as e:
                error_str = str(e).lower()
                
                # Handle specific error codes
                if '432' in str(e) or 'rate' in error_str or '429' in str(e):
                    wait_time = (2 ** attempt) + 1  # Exponential backoff starting at 3 seconds
                    logger.warning(f"Tavily rate limit hit (attempt {attempt + 1}), waiting {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
                    
                elif '401' in str(e) or 'unauthorized' in error_str or 'api key' in error_str:
                    logger.error("Tavily API key invalid or unauthorized")
                    return {'results': [], 'error': 'unauthorized'}
                    
                elif '432' in str(e) or 'usage limit' in error_str or 'plan' in error_str:
                    logger.error(f"Tavily usage limit exceeded: {e}")
                    logger.warning("💡 Consider getting a new Tavily API key or upgrading your plan")
                    logger.warning("🔄 Enabling fallback mode - trading will continue without web search")
                    self._tavily_fallback_mode = True
                    return {'results': [], 'error': 'usage_limit_exceeded'}
                    
                elif '400' in str(e) or 'bad request' in error_str:
                    logger.error(f"Tavily bad request: {e}")
                    return {'results': [], 'error': 'bad_request'}
                    
                else:
                    logger.error(f"Tavily search error (attempt {attempt + 1}): {e}")
                    if attempt == max_retries - 1:
                        return {'results': [], 'error': str(e)}
                    await asyncio.sleep(1 + attempt)  # Small backoff for other errors
        
        # If all retries failed
        return {'results': [], 'error': 'max_retries_exceeded'}
    
    async def autonomous_market_scan(self, research_mode: bool = False, deep_cycle: bool = False) -> List[Dict]:
        """
        GPT-5 scans the entire market using dynamic, intelligent search
        GPT generates its own search queries based on reasoning and market conditions
        
        Args:
            research_mode: If True, focuses on next-day catalysts and preparation
        """
        
        # Cooldown and caching to reduce API usage
        now = datetime.now()
        if self._last_market_scan_at and (now - self._last_market_scan_at).total_seconds() < self.scan_min_interval_seconds:
            return self._last_market_scan_result

        # Get current market context
        market_data = await self._get_market_context()
        
        # Determine if we're in research mode (market closed)
        clock = self.alpaca.get_clock()
        is_market_closed = not bool(getattr(clock, 'is_open', False))
        research_mode = research_mode or is_market_closed

        # Skip scans on weekends unless explicitly requested via research_mode
        now_et = datetime.now(pytz.utc).astimezone(pytz.timezone('US/Eastern'))
        if now_et.weekday() >= 5 and not research_mode:
            self._last_market_scan_at = datetime.now()
            self._last_market_scan_result = []
            logger.info("Weekend detected. Skipping market scan to conserve credits.")
            return []
        
        # Step 1: Let GPT generate intelligent search queries based on market conditions
        mode_context = "RESEARCH MODE - Preparing for next trading session" if research_mode else "LIVE TRADING MODE"
        
        # Eastern Time string for prompts
        et_now = datetime.now(pytz.utc).astimezone(pytz.timezone('US/Eastern'))
        search_generation_prompt = f"""
        Current Market Context:
        - Time: {et_now.strftime('%Y-%m-%d %H:%M:%S')} ET
        - Day: {et_now.strftime('%A')}
        - Market Status: {market_data['market_status']}
        - Mode: {mode_context}
        - SPY Change: {market_data['spy_change']}%
         - VIX Proxy (VIX index if available, else VIXY ETF): {market_data['vix_level']}
        
        {"Focus on TOMORROW's catalysts and overnight developments:" if research_mode else "Find IMMEDIATE trading opportunities:"}
        
        Generate 8-10 INTELLIGENT search queries to find {"tomorrow's opportunities" if research_mode else "trading opportunities NOW"}.
        Think like a hedge fund analyst - what information would give us an edge?
        
        Consider:
        1. What sectors are likely moving {"tomorrow" if research_mode else "today"} based on SPY/VIX?
        2. What time-sensitive events are happening (FDA, earnings, Fed)?
        3. What social sentiment shifts might be occurring?
        4. What technical setups are completing?
        5. What correlations or connections others might miss?
        
        {"RESEARCH MODE FOCUS:" if research_mode else "LIVE TRADING FOCUS:"}
        {'''
        - Tomorrow's pre-market catalysts (earnings before open)
        - FDA decisions or clinical trial results due
        - Asian/European market movements affecting US stocks
        - After-hours earnings reports from today
        - Reddit/Twitter sentiment building overnight
        - Gap up/down candidates for tomorrow
        - Stocks near technical breakouts
        ''' if research_mode else '''
        - Immediate catalysts driving moves NOW
        - Volume spikes and momentum plays
        - Breaking news and sudden developments  
        - Intraday technical setups
        - Options flow indicating big moves
        - Social media trending RIGHT NOW
        '''}
        
        Generate searches that will uncover:
        - Hidden catalysts before mainstream media
        - Social sentiment shifts (Reddit WSB, Twitter, StockTwits)
        - Unusual options flow or insider activity
        - Sector rotations or sympathy plays
        - Technical breakouts meeting fundamental catalysts
        
        Return a JSON array of search queries:
        {{
            "searches": [
                {{"query": "search string", "purpose": "what we're looking for"}},
                ...
            ]
        }}
        
        Be creative and think deeply. What would give us an edge TODAY specifically?
        """
        
        try:
            # Always allow GPT to generate searches, but control depth by mode
            response = await self._make_gpt_request(
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": search_generation_prompt}
                ],
                temperature=0.5,
                max_tokens=450 if self.cost_mode == 'low' else 600
            )
            search_data = self._parse_json_response(response.choices[0].message.content)
            searches = search_data.get('searches', [])
            logger.info(f"GPT generated {len(searches)} intelligent searches")
        except Exception as e:
            logger.info(f"Using default searches (fallback: {e})")
            searches = [
                {"query": f"reddit wallstreetbets trending stocks {datetime.now().strftime('%B %d')} sentiment", "purpose": "Social sentiment"},
                {"query": f"unusual options activity call sweeps {datetime.now().strftime('%B %d')}", "purpose": "Smart money flow"},
                {"query": f"FDA PDUFA calendar {datetime.now().strftime('%B %Y')} biotech catalysts", "purpose": "Upcoming catalysts"},
                {"query": "twitter financial trending stocks momentum social sentiment", "purpose": "Social momentum"},
                {"query": f"premarket movers gainers {datetime.now().strftime('%B %d')} news catalyst", "purpose": "Early movers"}
            ]
        
        # Prefer earnings list as seed to reduce Tavily usage
        earnings_seed = self._symbols_reporting_today_tomorrow()
        if earnings_seed:
            logger.debug(f"Using earnings calendar seed: {earnings_seed[:10]}")
            # Build targeted searches around a few earnings names
            earnings_queries = [
                {"query": f"{sym} earnings guidance upgrade downgrade {datetime.now().strftime('%B %d')}", "purpose": "Earnings catalyst"}
                for sym in earnings_seed[:5]
            ]
            searches = earnings_queries + searches

        # Step 2: Execute the searches (including social media)
        all_search_results = []
        # Query count controlled by deep_cycle and cost mode
        if deep_cycle:
            max_queries = 6 if self.cost_mode == 'low' else 8 if self.cost_mode == 'medium' else 10
        else:
            max_queries = 2 if self.cost_mode == 'low' else 3 if self.cost_mode == 'medium' else 4
        for search_item in searches[:max_queries]:
            query = search_item.get('query', search_item) if isinstance(search_item, dict) else search_item
            try:
                logger.debug(f"Searching: {query}")
                
                # Add social media focus for relevant searches
                if any(term in query.lower() for term in ['reddit', 'wsb', 'twitter', 'social', 'sentiment']):
                    # Search with social media focus
                    results = await self._safe_tavily_search(
                        query,
                        max_results=self.tavily_max_results,
                        include_domains=["reddit.com", "twitter.com", "stocktwits.com"] if 'reddit' in query.lower() or 'social' in query.lower() else None
                    )
                else:
                    # Regular search
                    results = await self._safe_tavily_search(
                        query,
                        max_results=self.tavily_max_results,
                        include_domains=self.tavily_include_domains
                    )
                
                all_search_results.append({
                    'query': query,
                    'purpose': search_item.get('purpose', 'General search') if isinstance(search_item, dict) else 'General search',
                    'results': results.get('results', [])
                })
            except Exception as e:
                logger.warning(f"Search failed for '{query}': {e}")
        
        # Step 3: Let GPT analyze initial results and generate follow-up searches if needed
        initial_analysis_prompt = f"""
        Initial search results from our queries:
        {json.dumps(all_search_results, indent=2)[:2000]}
        
        Analyze these results and identify:
        1. What patterns or opportunities are emerging?
        2. What SPECIFIC stocks or sectors need deeper investigation?
        3. What connections between different pieces of information do you see?
        
        Generate 3-5 FOLLOW-UP searches to dig deeper into the most promising leads.
        Think like a detective - what would confirm or deny these opportunities?
        
        Return JSON:
        {{
            "insights": "Brief summary of key findings",
            "follow_up_searches": [
                {{"query": "specific deeper search", "reason": "why this matters"}}
            ],
            "hot_symbols": ["SYMBOL1", "SYMBOL2", ...] // Symbols to investigate
        }}
        """
        
        # Let GPT reason about initial findings and search deeper
        follow_up_searches = []
        hot_symbols = []
        try:
            response = await self._make_gpt_request(
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": initial_analysis_prompt}
                ],
                temperature=0.4,
                max_tokens=450 if self.cost_mode == 'low' else 600
            )
            follow_up_data = self._parse_json_response(response.choices[0].message.content)
            follow_up_searches = follow_up_data.get('follow_up_searches', [])
            hot_symbols = follow_up_data.get('hot_symbols', [])
            insights = follow_up_data.get('insights', '')
            if insights:
                logger.info(f"GPT insights: {insights[:200]}")
            # Execute follow-up searches (controlled by mode + deep_cycle)
            follow_up_limit = (2 if self.cost_mode == 'low' else 3) if deep_cycle else 1
            for follow_up in follow_up_searches[:follow_up_limit]:
                query = follow_up.get('query', follow_up) if isinstance(follow_up, dict) else follow_up
                try:
                    logger.debug(f"Follow-up search: {query}")
                    results = await self._safe_tavily_search(query, max_results=self.tavily_max_results)
                    all_search_results.append({
                        'query': query,
                        'purpose': f"FOLLOW-UP: {follow_up.get('reason', '')}",
                        'results': results.get('results', [])
                    })
                except:
                    pass
                    
        except Exception as e:
            logger.warning(f"Follow-up search generation failed: {e}")
        
        # If we failed to gather any web intelligence, do not fabricate ideas
        try:
            total_search_results = sum(len(item.get('results', [])) for item in all_search_results)
        except Exception:
            total_search_results = 0
        if total_search_results == 0:
            logger.info("Skipping new opportunity search due to insufficient web intel (Tavily unavailable or no results). Managing existing positions only.")
            # Cache empty result to respect scan cadence
            self._last_market_scan_at = datetime.now()
            self._last_market_scan_result = []
            return []

        # Step 4: Get real-time data for hot symbols identified by GPT
        market_movers = []
        
        # Add GPT-identified hot symbols to check list
        symbols_to_check = list({s.upper() for s in hot_symbols[:5]})
        
        for symbol in symbols_to_check:
            try:
                snapshot = self.alpaca.get_snapshot(symbol, feed='iex')
                if snapshot and snapshot.daily_bar:
                    change_pct = ((snapshot.latest_trade.price - snapshot.daily_bar.open) / 
                                 snapshot.daily_bar.open * 100)
                    if abs(change_pct) > 0.5:  # Lower threshold for GPT-identified symbols
                        market_movers.append({
                            'symbol': symbol,
                            'change_pct': change_pct,
                            'volume': snapshot.daily_bar.volume,
                            'price': snapshot.latest_trade.price,
                            'gpt_identified': symbol in hot_symbols
                        })
            except:
                pass
        
        # Step 5: Final GPT analysis with all data including follow-ups
        analysis_prompt = f"""
        You've conducted intelligent searches and follow-ups. Now connect the dots.
        
        Market Context:
        - Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} EST
        - SPY: {market_data['spy_change']}%
        - VIX: {market_data['vix_level']}
        
        All Search Results (including follow-ups):
        {json.dumps(all_search_results, indent=2)[:4000]}
        
        Live Market Data:
        {json.dumps(market_movers, indent=2)}
        
        USE YOUR REASONING to identify opportunities by:
        1. Connecting information across different searches
        2. Identifying patterns others might miss
        3. Finding stocks mentioned in social media AND news
        4. Spotting sector rotations or sympathy plays
        5. Detecting early-stage momentum before it's obvious
        
        Provide opportunities in JSON format:
        {{
            "reasoning": "Your analytical thought process and connections you found",
            "opportunities": [
                {{
                    "symbol": "TICKER",
                    "catalyst": "Specific catalyst you discovered",
                    "social_sentiment": "What Reddit/Twitter is saying",
                    "entry_price": 0.00,
                    "stop_loss": 0.00,
                    "target_1": 0.00,
                    "target_move": 10.0,
                    "confidence": 75,
                    "time_hours": 6,
                    "connection": "How different pieces of info connect"
                }}
            ]
        }}
        
        Focus on opportunities with:
        - Multiple confirming signals (news + social + technical)
        - Information asymmetry (you found something others haven't)
        - Clear catalyst within 48 hours
        - Strong social momentum building
        
        BE CREATIVE. THINK DEEPLY. FIND THE EDGE.
        """
        
        try:
            # GPT analyzes the real search results
            response = await self._make_gpt_request(
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": analysis_prompt}
                ],
                temperature=0.3,
                max_tokens=900
            )
            
            # Parse opportunities from GPT response
            response_data = self._parse_json_response(response.choices[0].message.content)
            
            # Log GPT's reasoning
            reasoning = response_data.get('reasoning', '')
            if reasoning:
                logger.info(f"GPT Reasoning: {reasoning[:300]}...")
            
            # Extract opportunities
            opportunities = response_data.get('opportunities', [])
            
            # Ensure proper format for each opportunity
            formatted_opportunities = []
            for opp in opportunities:
                if isinstance(opp, dict) and 'symbol' in opp:
                    formatted_opp = {
                        'symbol': opp.get('symbol', '').upper(),
                        'catalyst': opp.get('catalyst', 'Market momentum'),
                        'social_sentiment': opp.get('social_sentiment', 'N/A'),
                        'current_price': float(opp.get('current_price', 0)),
                        'entry_price': float(opp.get('entry_price', 0)),
                        'stop_loss': float(opp.get('stop_loss', 0)),
                        'target_1': float(opp.get('target_1', 0)),
                        'target_move': float(opp.get('target_move', 5)),
                        'confidence': int(opp.get('confidence', 60)),
                        'time_hours': int(opp.get('time_hours', 6)),
                        'connection': opp.get('connection', ''),
                        'risk_factors': opp.get('risk_factors', 'Market volatility')
                    }
                    formatted_opportunities.append(formatted_opp)
            
            opportunities = formatted_opportunities
            
            # Validate and enhance opportunities with real-time data
            validated_opportunities = []
            for opp in opportunities:
                try:
                    # Get real-time price for validation
                    snapshot = self.alpaca.get_snapshot(opp['symbol'], feed='iex')
                    if snapshot and snapshot.latest_trade:
                        opp['current_price'] = snapshot.latest_trade.price
                        opp['validated'] = True
                        validated_opportunities.append(opp)
                        logger.info(f"✓ Validated: {opp['symbol']} @ ${opp['current_price']:.2f} - {opp['catalyst'][:50]}")
                except Exception as e:
                    logger.warning(f"Could not validate {opp.get('symbol', 'Unknown')}: {e}")
            
            # Rank by expected value
            for opp in validated_opportunities:
                opp['expected_value'] = (
                    opp.get('confidence', 50) / 100 * 
                    opp.get('target_move', 5) * 
                    (1 / max(opp.get('time_hours', 24), 1))
                )
            
            validated_opportunities.sort(key=lambda x: x.get('expected_value', 0), reverse=True)
            
            logger.info(f"GPT-5 found {len(validated_opportunities)} validated opportunities")
            for opp in validated_opportunities[:3]:
                logger.info(f"  {opp['symbol']}: {opp.get('catalyst', 'No catalyst')[:60]} "
                          f"(Confidence: {opp.get('confidence', 0)}%, "
                          f"Target: {opp.get('target_move', 0)}%)")
            
            # Cache results with timestamp
            self._last_market_scan_at = datetime.now()
            self._last_market_scan_result = validated_opportunities
            return validated_opportunities
            
        except Exception as e:
            logger.error(f"GPT analysis failed: {e}")
            return []
    
    async def deep_analysis(self, symbol: str) -> Dict:
        """
        GPT-5 performs deep analysis on a specific opportunity
        This is where GPT-5's reasoning capabilities shine
        """
        
        # Step 0: Fast pre-GPT confidence scoring to filter out low EV names
        try:
            current_data_quick = await self._get_current_data(symbol)
        except Exception:
            current_data_quick = {}

        pre_score = self._compute_confidence_score(
            catalyst_strength=0,  # filled after searches
            news_recency_hours=999,  # unknown yet
            price_change_pct=0.0,
            volume_vs_avg=1.0,
            technical_readiness=False,
            liquidity_good=True if current_data_quick else True
        )
        if pre_score < self.pre_gpt_min_score:
            return {
                'decision': 'NO-GO',
                'confidence': pre_score,
                'reasoning': 'Filtered by pre-GPT score'
            }

        # Step 1: Gather real web data about the symbol
        search_results = {}
        try:
            # Search for recent news and analysis
            searches = [
                f"{symbol} stock news today {datetime.now().strftime('%B %Y')}",
                f"{symbol} analyst rating price target upgrade downgrade",
                f"{symbol} earnings report guidance forecast",
                f"{symbol} insider trading buying selling",
                f"{symbol} options flow unusual activity"
            ]
            
            for search_query in searches[:1]:  # Further limit to reduce credits
                try:
                    results = await self._safe_tavily_search(
                        search_query,
                        max_results=self.tavily_max_results,
                        include_domains=self.tavily_include_domains
                    )
                    search_results[search_query] = results.get('results', [])
                except Exception as e:
                    logger.warning(f"Search failed: {e}")
        except:
            pass
        
        # Step 2: Get technical data from Alpaca
        try:
            current_data = await self._get_current_data(symbol)
            
            # Get historical bars for technical analysis
            bars = self.alpaca.get_bars(symbol, '1Day', limit=30, feed='iex').df
            if not bars.empty:
                current_data['avg_volume_30d'] = bars['volume'].mean()
                current_data['high_52w'] = bars['high'].max()
                current_data['low_52w'] = bars['low'].min()
                current_data['volatility'] = bars['close'].pct_change().std() * 100
        except Exception as e:
            logger.warning(f"Failed to get technical data: {e}")
            current_data = {}
        
        # Step 3: Analyze with GPT (aggressive prompt variant if risky)
        analysis_prompt = f"""
        Perform deep analysis on {symbol} using this real-time data:
        
        Current Market Data:
        {json.dumps(current_data, indent=2)}
        
        Recent News & Analysis:
        {json.dumps(search_results, indent=2)[:2000]}
        
        Based on this data, provide your analysis in this EXACT JSON format:
        {{
            "decision": "GO or NO-GO",
            "symbol": "{symbol}",
            "confidence": 75,
            "position_size_pct": 0.15,
            "entry_price": 0.00,
            "stop_loss": 0.00,
            "target_1": 0.00,
            "target_2": 0.00,
            "target_3": 0.00,
            "reasoning": "Detailed explanation of the trade thesis",
            "catalysts": "Upcoming catalysts that could drive price",
            "risks": "Key risks to monitor",
            "timeframe": "Expected holding period"
        }}
        
        Decision Criteria:
        - GO: Clear catalyst, good risk/reward (1:3+), confidence > 65%
        - NO-GO: Unclear thesis, poor risk/reward, or too risky
        
        Be brutally honest. Only recommend GO for high-conviction trades.
        Consider:
        1. Is there a clear catalyst not yet priced in?
        2. Is the risk/reward favorable (at least 1:3)?
        3. Is there strong momentum or a clear trend?
        4. Are there any red flags in the news?
        
        RESPOND ONLY WITH THE JSON, NO OTHER TEXT.
        """

        # Aggressive variant scaffold used implicitly by the system prompt when category=aggressive
        if self._estimate_symbol_category(symbol) == 'aggressive':
            analysis_prompt = f"""
            Analyze {symbol} for EXPLOSIVE move potential (high-beta/aggressive):
            
            Market Data:
            {json.dumps(current_data, indent=2)}
            
            News & Signals:
            {json.dumps(search_results, indent=2)[:2000]}
            
            CRITICAL FACTORS:
            1. Catalyst magnitude (0-10)
            2. Float / squeeze dynamics
            3. Options flow / sentiment shift
            4. Technical coil / breakout readiness
            5. Top risks
            
            Return STRICT JSON:
            {{
              "decision": "GO" | "NO-GO",
              "symbol": "{symbol}",
              "confidence": 70,
              "position_size_pct": 0.05,
              "entry_price": 0.00,
              "stop_loss": 0.00,
              "target_1": 0.00,
              "reasoning": "...",
              "category": "aggressive"
            }}
            """
        
        # Respect per-symbol cooldown
        last = self._last_analysis_by_symbol.get(symbol)
        now = datetime.now()
        if last and (now - last.get('ts', now)).total_seconds() < self.deep_analysis_min_interval_seconds:
            return last['result']

        try:
            # GPT-5 performs deep analysis
            response = await self._make_gpt_request(
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": analysis_prompt}
                ],
                temperature=0.2,  # Even more focused for analysis
                max_tokens=900
            )
            
            # Parse the analysis
            analysis = self._parse_analysis(response.choices[0].message.content)
            
            # Validate prices with real data
            if current_data.get('price'):
                if analysis['entry_price'] == 0:
                    analysis['entry_price'] = current_data['price'] * 1.001  # Slightly above current
                if analysis['stop_loss'] == 0:
                    analysis['stop_loss'] = current_data['price'] * 0.97  # 3% stop
                if analysis['target_1'] == 0:
                    analysis['target_1'] = current_data['price'] * 1.05  # 5% target
            
            # Add to AI memory for learning (convert to JSON-safe types)
            self.ai_memory.append({
                'symbol': str(symbol),
                'analysis': {k: (int(v) if isinstance(v, (np.integer, np.int64)) else 
                            float(v) if isinstance(v, (np.floating, np.float64)) else 
                            str(v) if isinstance(v, datetime) else v)
                            for k, v in analysis.items()},
                'timestamp': datetime.now().isoformat()
            })
            
            logger.info(f"Analysis for {symbol}: {analysis['decision']} "
                       f"(Confidence: {analysis['confidence']}%)")
            
            # Cache
            self._last_analysis_by_symbol[symbol] = {'ts': datetime.now(), 'result': analysis}
            return analysis
            
        except Exception as e:
            logger.error(f"Deep analysis failed for {symbol}: {e}")
            return {'decision': 'NO-GO', 'error': str(e)}
    
    async def execute_trade(self, trade_plan: Dict) -> bool:
        """
        Execute trade based on GPT-5's plan
        """
        try:
            symbol = trade_plan['symbol']
            
            # Check risk limits
            if not self._check_risk_limits(trade_plan):
                logger.warning(f"Trade rejected by risk limits: {symbol}")
                return False
            
            # Determine category and enforce allocation caps
            category = trade_plan.get('category') or self._estimate_symbol_category(symbol)
            if category not in ('aggressive', 'conservative'):
                category = 'conservative'
            
            # Calculate position size
            account = self.alpaca.get_account()
            portfolio_value = float(account.portfolio_value)
            requested_pct = float(trade_plan.get('position_size_pct', 0.05))

            # Volatility-adjusted cap for aggressive plays
            vol_pct = 0.0
            try:
                bars = self.alpaca.get_bars(symbol, '1Day', limit=30, feed='iex').df
                if not bars.empty:
                    vol_pct = float(bars['close'].pct_change().std() * 100)
            except Exception:
                pass

            if category == 'aggressive':
                requested_pct = min(requested_pct, 0.10)  # hard cap per trade
                if vol_pct > 100:
                    requested_pct *= 0.5  # reduce size for ultra high vol

            # Enforce category allocation cap based on current exposure
            current_category_value = self._current_category_exposure(category)
            max_category_value = portfolio_value * (self.aggressive_allocation_pct if category == 'aggressive' else self.safe_allocation_pct)
            remaining_category_value = max(0.0, max_category_value - current_category_value)
            position_size = min(portfolio_value * requested_pct, remaining_category_value)
            if position_size <= 0:
                logger.info(f"Skipping {symbol}: no remaining allocation for {category} bucket")
                return False
            
            # Calculate shares
            current_price = float(self.alpaca.get_latest_trade(symbol).price)
            shares = int(position_size / current_price)
            
            if shares < 1:
                logger.warning(f"Position too small: {symbol}")
                return False
            
            # Place order with Alpaca - EXTENDED HOURS ENABLED
            order = self.alpaca.submit_order(
                symbol=symbol,
                qty=shares,
                side='buy',
                type='limit',
                limit_price=trade_plan['entry_price'],
                time_in_force='day',
                extended_hours=True,  # Enable extended hours trading
                order_class='bracket',
                stop_loss={'stop_price': trade_plan['stop_loss']},
                take_profit={'limit_price': trade_plan['target_1']}
            )
            
            logger.info(f"✅ GPT-5 executed trade: {symbol}")
            logger.info(f"  Shares: {shares}")
            logger.info(f"  Entry: ${trade_plan['entry_price']:.2f}")
            logger.info(f"  Stop: ${trade_plan['stop_loss']:.2f}")
            logger.info(f"  Target: ${trade_plan['target_1']:.2f}")
            logger.info(f"  Confidence: {trade_plan['confidence']}%")
            logger.info(f"  Category: {category} | Requested%: {requested_pct*100:.1f} | Alloc used: ${position_size:,.2f}")
            logger.info(f"  Reasoning: {trade_plan.get('reasoning', 'N/A')[:200]}")
            
            # Track category mapping
            self._category_by_symbol[symbol] = category
            
            return True
            
        except Exception as e:
            logger.error(f"Trade execution failed: {e}")
            return False
    
    async def manage_positions(self):
        """
        GPT-5 manages existing positions intelligently
        Monitors news, adjusts stops, takes profits, or exits based on real-time analysis
        """
        positions = self.alpaca.list_positions()
        
        if not positions:
            logger.debug("No open positions to manage")
            return
        
        logger.info(f"📊 Managing {len(positions)} position(s)")
        
        for position in positions:
            symbol = position.symbol
            entry_price = float(position.avg_entry_price)
            current_price = float(position.current_price)
            pnl_pct = float(position.unrealized_plpc) * 100
            shares = int(position.qty)
            
            # Search for real-time updates on this position
            # Only run heavy GPT management at a lower cadence or when thresholds trigger
            if self._last_position_management_at:
                seconds_since = (datetime.now() - self._last_position_management_at).total_seconds()
                if seconds_since < self.position_management_min_interval_seconds and abs(pnl_pct) < 5:
                    continue
            try:
                position_search = await self._safe_tavily_search(
                    f"{symbol} stock news latest {datetime.now().strftime('%B %d')}",
                    max_results=self.tavily_max_results,
                    include_domains=self.tavily_include_domains
                )
                search_results = position_search.get('results', [])
            except:
                search_results = []
            
            management_prompt = f"""
            Analyze my current {symbol} position with real-time data:
            
            POSITION DETAILS:
            - Entry: ${entry_price:.2f}
            - Current: ${current_price:.2f}
            - P&L: {pnl_pct:.2f}% ({'+' if pnl_pct > 0 else ''}${(current_price - entry_price) * shares:.2f})
            - Shares: {shares}
            
            LATEST NEWS/DEVELOPMENTS:
            {json.dumps(search_results, indent=2)[:1000]}
            
            DECISION FRAMEWORK:
            - If up >5%: Consider trailing stop or partial profit
            - If up >10%: Take 50% profits, trail the rest
            - If down >3%: Re-evaluate thesis, possibly exit
            - If news is negative: Exit immediately
            - If momentum accelerating: Raise targets
            
            Analyze and decide:
            1. HOLD - Thesis intact, continue as planned
            2. TRIM - Take partial profits (specify %)
            3. EXIT - Close entire position now
            4. TRAIL - Move stop up to lock profits
            5. ADD - Double down (only if strong new catalyst)
            
            Return JSON:
            {{
                "action": "HOLD/TRIM/EXIT/TRAIL/ADD",
                "reasoning": "Why this decision",
                "new_stop": 0.00,  // If trailing
                "trim_percent": 50,  // If trimming
                "urgency": "high/medium/low"
            }}
            """
            
            try:
                response = await self._make_gpt_request(
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": management_prompt}
                    ],
                    temperature=0.2,
                    max_tokens=500
                )
                
                decision = self._parse_json_response(response.choices[0].message.content)
                action = decision.get('action', 'HOLD')
                reasoning = decision.get('reasoning', '')
                
                logger.info(f"  {symbol}: {action} - {reasoning[:100]}")
                
                # Execute the management decision
                if action == 'EXIT':
                    # Market sell immediately
                    self.alpaca.submit_order(
                        symbol=symbol,
                        qty=shares,
                        side='sell',
                        type='market',
                        time_in_force='day'
                    )
                    logger.warning(f"🔴 EXITED {symbol}: {reasoning}")
                    
                elif action == 'TRIM' and decision.get('trim_percent'):
                    # Sell partial position
                    trim_shares = int(shares * decision['trim_percent'] / 100)
                    if trim_shares > 0:
                        self.alpaca.submit_order(
                            symbol=symbol,
                            qty=trim_shares,
                            side='sell',
                            type='market',
                            time_in_force='day'
                        )
                        logger.info(f"✂️ TRIMMED {trim_shares} shares of {symbol}")
                        
                elif action == 'TRAIL' and decision.get('new_stop'):
                    # Update stop loss (would need to cancel/replace order)
                    logger.info(f"📈 TRAILING stop for {symbol} to ${decision['new_stop']:.2f}")
                    
                elif action == 'ADD':
                    # Could add to position if we want
                    logger.info(f"🎯 Considering adding to {symbol}")
                
                # Default is HOLD - do nothing
                
            except Exception as e:
                logger.error(f"Failed to manage {symbol}: {e}")
        self._last_position_management_at = datetime.now()
    
    async def learn_and_adapt(self):
        """
        GPT-5 learns from its trades and adapts strategy
        """
        # Get recent trades
        trades = self.alpaca.list_orders(status='closed', limit=50)
        
        learning_prompt = f"""
        Analyze my recent trading performance:
        
        {self._format_trades_for_analysis(trades)}
        
        Identify:
        1. What patterns led to wins?
        2. What patterns led to losses?
        3. Were stops too tight or too loose?
        4. Were targets too conservative?
        5. Which catalysts worked best?
        6. Which times of day were most profitable?
        
        Adapt the strategy:
        1. What should we do MORE of?
        2. What should we STOP doing?
        3. How should we adjust position sizing?
        4. Should we focus on specific sectors?
        5. Are we entering too early or too late?
        
        Update trading rules for tomorrow.
        """
        
        response = await self._make_gpt_request(
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": learning_prompt}
            ],
            temperature=0.4
        )
        
        # Store learnings
        self.successful_patterns.append({
            'date': datetime.now(),
            'learnings': response.choices[0].message.content
        })
        
        logger.info("GPT-5 learning update completed")
    
    # Helper methods
    def _init_tavily_buckets(self) -> None:
        """Initialize daily credit buckets for premarket, intraday, and buffer."""
        # Split: 40% premarket, 40% intraday, 20% buffer
        total = self.tavily_daily_credit_budget
        self._tavily_bucket_premarket = int(total * 0.4)
        self._tavily_bucket_intraday = int(total * 0.4)
        self._tavily_bucket_buffer = total - self._tavily_bucket_premarket - self._tavily_bucket_intraday
        self._tavily_bucket_last_date = datetime.now().date()

    def _check_tavily_bucket_allowance(self) -> bool:
        """Check if current time window has credits left; reset buckets at midnight."""
        today = datetime.now().date()
        if self._tavily_bucket_last_date != today:
            self._init_tavily_buckets()
        et_now = datetime.now(pytz.utc).astimezone(pytz.timezone('US/Eastern'))
        hour = et_now.hour
        # Premarket window ~ 07:00–09:30 ET (conservative)
        if 7 <= hour < 10:
            return self._tavily_bucket_premarket > 0 or self._tavily_bucket_buffer > 0
        # Intraday window ~ 09:30–16:00 ET
        if 9 <= hour < 16:
            return self._tavily_bucket_intraday > 0 or self._tavily_bucket_buffer > 0
        # Otherwise: allow only buffer
        return self._tavily_bucket_buffer > 0

    def _consume_tavily_bucket_credit(self) -> None:
        et_now = datetime.now(pytz.utc).astimezone(pytz.timezone('US/Eastern'))
        hour = et_now.hour
        if 7 <= hour < 10 and self._tavily_bucket_premarket > 0:
            self._tavily_bucket_premarket -= 1
            return
        if 9 <= hour < 16 and self._tavily_bucket_intraday > 0:
            self._tavily_bucket_intraday -= 1
            return
        if self._tavily_bucket_buffer > 0:
            self._tavily_bucket_buffer -= 1

    def _load_earnings_calendar(self) -> None:
        """Load earnings calendar from data/earnings_calendar.csv if available."""
        try:
            import csv
            cal_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'earnings_calendar.csv')
            if not os.path.exists(cal_path):
                return
            with open(cal_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Expect columns: date (YYYY-MM-DD), symbol
                    d = row.get('date')
                    s = row.get('symbol', '').upper()
                    if not d or not s:
                        continue
                    self._earnings_by_date.setdefault(d, []).append(s)
        except Exception as e:
            logger.debug(f"Earnings calendar load skipped: {e}")

    def _symbols_reporting_today_tomorrow(self) -> List[str]:
        try:
            today = datetime.now().date()
            days = [today.isoformat(), (today + timedelta(days=1)).isoformat()]
            symbols = []
            for d in days:
                symbols.extend(self._earnings_by_date.get(d, []))
            return list(sorted(set(symbols)))
        except Exception:
            return []
    async def _get_market_context(self) -> Dict:
        """Get current market conditions using best available data source"""
        spy_change = 0.0
        vix_level = 20.0
        data_source = 'default'
        clock = None
        
        try:
            # Primary: Use Alpaca for real-time SPY data
            clock = self.alpaca.get_clock()
            # Determine weekday to handle weekend data sources more conservatively
            now_et = datetime.now(pytz.utc).astimezone(pytz.timezone('US/Eastern'))
            weekday = now_et.weekday()  # Mon=0..Sun=6
            is_weekend = weekday >= 5
            
            if clock.is_open:
                # During market hours, get intraday data (use IEX feed, not SIP)
                try:
                    spy_snapshot = self.alpaca.get_snapshot('SPY', feed='iex')
                except:
                    # Fallback to bars if snapshot fails
                    spy_snapshot = None
                    
                spy_daily_bar = spy_snapshot.daily_bar if spy_snapshot else None
                if spy_daily_bar:
                    spy_change = ((spy_daily_bar.close - spy_daily_bar.open) / 
                                 spy_daily_bar.open * 100)
                    logger.debug(f"SPY change from Alpaca: {spy_change:.2f}%")
                    data_source = 'alpaca'
            else:
                # After hours, get last close
                spy_bars = self.alpaca.get_bars('SPY', '1Day', limit=1, feed='iex').df
                if not spy_bars.empty:
                    spy_change = 0.0  # No intraday change after hours
                    data_source = 'alpaca'
                    
            # Get volatility indicator (VIXY as VIX proxy)
            # Weekends: avoid '^VIX' since many providers return empty; prefer VIXY snapshot or default
            try:
                if not is_weekend:
                    vix = yf.Ticker('^VIX')
                    vix_hist = vix.history(period='1d')
                    if not vix_hist.empty:
                        vix_level = float(vix_hist['Close'].iloc[-1])
                        logger.debug(f"VIX level from yfinance: {vix_level:.2f}")
                if is_weekend or vix_level == 20.0:
                    # Try VIXY snapshot as a proxy
                    try:
                        vixy_snapshot = self.alpaca.get_snapshot('VIXY', feed='iex')
                        if vixy_snapshot and vixy_snapshot.latest_trade:
                            vix_level = float(vixy_snapshot.latest_trade.price)
                    except Exception:
                        pass
            except Exception:
                # Fall back to default if all else fails
                vix_level = vix_level or 20.0
                
        except Exception as e:
            logger.warning(f"Alpaca data fetch failed: {e}")
            
            # Fallback: Try yfinance for backup data
            try:
                spy = yf.Ticker('SPY')
                spy_hist = spy.history(period='1d', interval='5m', prepost=True)
                if not spy_hist.empty:
                    spy_change = ((spy_hist['Close'].iloc[-1] - spy_hist['Open'].iloc[0]) / 
                                 spy_hist['Open'].iloc[0] * 100)
                    logger.debug(f"SPY change from yfinance backup: {spy_change:.2f}%")
                    data_source = 'yfinance'
            except:
                logger.warning("Both data sources failed, using defaults")
        
        return {
            'market_status': 'open' if clock and getattr(clock, 'is_open', False) else 'closed',
            'spy_change': round(spy_change, 2),
            'vix_level': round(vix_level, 2),
            'data_source': data_source
        }
    
    async def _get_current_data(self, symbol: str) -> Dict:
        """Get current price and volume data"""
        try:
            snapshot = self.alpaca.get_snapshot(symbol, feed='iex')
            return {
                'price': snapshot.latest_trade.price if snapshot.latest_trade else 0,
                'volume': snapshot.latest_trade.size if snapshot.latest_trade else 0,
                'bid': snapshot.latest_quote.bid_price if snapshot.latest_quote else 0,
                'ask': snapshot.latest_quote.ask_price if snapshot.latest_quote else 0,
                'spread': (snapshot.latest_quote.ask_price - snapshot.latest_quote.bid_price) if snapshot.latest_quote else 0
            }
        except Exception as e:
            logger.debug(f"Could not get data for {symbol}: {e}")
            return {}
    
    async def _make_gpt_request(self, messages: list, temperature: float = 0.3, max_tokens: int = 2000) -> any:
        """
        Make a GPT request with automatic model fallback on rate limits
        """
        # Budget check (rolling 1h window)
        now = datetime.now()
        while self._gpt_call_times and (now - self._gpt_call_times[0]).total_seconds() > 3600:
            self._gpt_call_times.popleft()
        if len(self._gpt_call_times) >= self.max_gpt_requests_per_hour:
            raise Exception("OpenAI budget exhausted for this hour; skipping GPT call")

        for attempt in range(len(self.model_hierarchy)):
            try:
                # Log which model we're using
                if self.current_model_index > 0:
                    logger.info(f"Using fallback model: {self.model}")
                else:
                    logger.debug(f"Using primary model: {self.model}")
                
                # Make the API call
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=min(max_tokens, self.max_tokens_cap),
                )
                
                # Record budget usage
                self._gpt_call_times.append(now)

                # If successful and we were in fallback, try to move back up
                if self.current_model_index > 0 and self.rate_limit_errors == 0:
                    # Been 5 minutes since last rate limit? Try better model
                    if self.last_rate_limit_time and (datetime.now() - self.last_rate_limit_time).seconds > 300:
                        self.current_model_index = max(0, self.current_model_index - 1)
                        self.model = self.model_hierarchy[self.current_model_index]
                        logger.info(f"Upgrading back to: {self.model}")
                
                return response
                
            except Exception as e:
                error_message = str(e).lower()
                
                # Check if it's a rate limit error
                if 'rate_limit' in error_message or '429' in error_message or 'quota' in error_message:
                    self.rate_limit_errors += 1
                    self.last_rate_limit_time = datetime.now()
                    
                    # Try next model in hierarchy
                    if self.current_model_index < len(self.model_hierarchy) - 1:
                        self.current_model_index += 1
                        self.model = self.model_hierarchy[self.current_model_index]
                        logger.warning(f"Rate limited on {self.model_hierarchy[self.current_model_index-1]}, falling back to {self.model}")
                        continue
                    else:
                        logger.error("All models exhausted, waiting 60 seconds...")
                        await asyncio.sleep(60)
                        # Reset to try again from the current level
                        continue
                
                # Check if it's an invalid model error (e.g., no access to gpt-5)
                elif ('model' in error_message and ('not found' in error_message or 'does not exist' in error_message or 'model_not_found' in error_message)) or '404' in str(e):
                    if self.current_model_index < len(self.model_hierarchy) - 1:
                        self.current_model_index += 1
                        self.model = self.model_hierarchy[self.current_model_index]
                        logger.warning(f"No access to {self.model_hierarchy[self.current_model_index-1]}, using {self.model}")
                        continue
                
                # Other errors - just raise
                else:
                    logger.error(f"GPT API error: {e}")
                    raise e
        
        # If we get here, all attempts failed
        raise Exception("All model attempts failed")
    
    def _parse_json_response(self, gpt_response: str) -> Dict:
        """Generic JSON parser for GPT responses"""
        try:
            response_text = gpt_response.strip()
            if '{' in response_text and '}' in response_text:
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                json_str = response_text[start_idx:end_idx]
                return json.loads(json_str)
        except:
            pass
        return {}
    
    def _parse_opportunities(self, gpt_response: str) -> List[Dict]:
        """Parse opportunities from GPT-5 response"""
        try:
            # Clean the response to extract JSON
            response_text = gpt_response.strip()
            
            # Try to find JSON in the response
            if '{' in response_text and '}' in response_text:
                # Extract JSON portion
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                json_str = response_text[start_idx:end_idx]
                
                # Parse JSON
                data = json.loads(json_str)
                
                # Extract opportunities
                if 'opportunities' in data:
                    opportunities = data['opportunities']
                elif isinstance(data, list):
                    opportunities = data
                else:
                    # Single opportunity
                    opportunities = [data]
                
                # Validate and clean each opportunity
                valid_opportunities = []
                for opp in opportunities:
                    if isinstance(opp, dict) and 'symbol' in opp:
                        # Ensure required fields with defaults
                        clean_opp = {
                            'symbol': opp.get('symbol', '').upper(),
                            'catalyst': opp.get('catalyst', 'Market momentum'),
                            'current_price': float(opp.get('current_price', 0)),
                            'entry_price': float(opp.get('entry_price', 0)),
                            'stop_loss': float(opp.get('stop_loss', 0)),
                            'target_1': float(opp.get('target_1', 0)),
                            'target_move': float(opp.get('target_move', 5)),
                            'confidence': int(opp.get('confidence', 60)),
                            'time_hours': int(opp.get('time_hours', 6)),
                            'risk_factors': opp.get('risk_factors', 'Market volatility')
                        }
                        valid_opportunities.append(clean_opp)
                
                return valid_opportunities
                
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response: {e}")
            logger.debug(f"Response was: {gpt_response[:500]}")
        except Exception as e:
            logger.error(f"Error parsing opportunities: {e}")
        
        return []
    
    def _parse_analysis(self, gpt_response: str) -> Dict:
        """Parse analysis from GPT-5 response"""
        try:
            # Try to parse as JSON first
            if '{' in gpt_response and '}' in gpt_response:
                start_idx = gpt_response.find('{')
                end_idx = gpt_response.rfind('}') + 1
                json_str = gpt_response[start_idx:end_idx]
                data = json.loads(json_str)
                
                return {
                    'decision': data.get('decision', 'NO-GO'),
                    'symbol': data.get('symbol', ''),
                    'confidence': int(data.get('confidence', 50)),
                    'position_size_pct': float(data.get('position_size_pct', 0.05)),
                    'entry_price': float(data.get('entry_price', 0)),
                    'stop_loss': float(data.get('stop_loss', 0)),
                    'target_1': float(data.get('target_1', 0)),
                    'target_2': float(data.get('target_2', 0)),
                    'target_3': float(data.get('target_3', 0)),
                    'reasoning': data.get('reasoning', gpt_response[:500])
                }
        except:
            pass
        
        # Fallback: Parse text response
        decision = 'GO' if 'GO' in gpt_response.upper() and 'NO-GO' not in gpt_response.upper() else 'NO-GO'
        
        # Try to extract confidence score
        confidence = 60
        if 'confidence' in gpt_response.lower():
            import re
            match = re.search(r'confidence[:\s]+(\d+)', gpt_response.lower())
            if match:
                confidence = int(match.group(1))
        
        return {
            'decision': decision,
            'confidence': confidence,
            'position_size_pct': 0.10 if confidence > 70 else 0.05,
            'entry_price': 0,
            'stop_loss': 0,
            'target_1': 0,
            'reasoning': gpt_response[:500]
        }

    def _compute_confidence_score(
        self,
        catalyst_strength: int,
        news_recency_hours: float,
        price_change_pct: float,
        volume_vs_avg: float,
        technical_readiness: bool,
        liquidity_good: bool
    ) -> int:
        """Lightweight, deterministic pre-GPT confidence score (0-100)."""
        # Catalyst strength (0-40)
        cat = max(0, min(40, catalyst_strength))
        # Recency (0-15): <=24h => 15, else decay
        if news_recency_hours <= 24:
            rec = 15
        elif news_recency_hours <= 48:
            rec = 8
        else:
            rec = 0
        # Price/volume confirmation (0-25)
        pv = 0
        if abs(price_change_pct) >= 2:
            pv += 10
        if volume_vs_avg >= 2:
            pv += 15
        pv = min(pv, 25)
        # Technical (0-10)
        tech = 10 if technical_readiness else 0
        # Liquidity (0-10)
        liq = 10 if liquidity_good else 0
        score = cat + rec + pv + tech + liq
        return int(max(0, min(100, score)))
    
    def _check_risk_limits(self, trade_plan: Dict) -> bool:
        """Check if trade meets risk parameters"""
        # Check position size
        if trade_plan.get('position_size_pct', 0) > self.risk_limits['max_position_pct']:
            return False
        
        # Check confidence (trade_plan confidence is integer percent)
        if trade_plan.get('confidence', 0) < self.risk_limits['min_confidence']:
            return False
        
        # Check number of positions
        positions = self.alpaca.list_positions()
        if len(positions) >= self.risk_limits['max_positions']:
            return False

        # Check daily loss limit (block new trades if hit)
        try:
            account = self.alpaca.get_account()
            equity = float(account.equity)
            last_equity = float(account.last_equity)
            if last_equity > 0:
                drawdown = (equity - last_equity) / last_equity
                if drawdown < -self.risk_limits['max_daily_loss_pct']:
                    logger.warning(
                        f"Daily loss limit hit: {drawdown*100:.1f}% < -{self.risk_limits['max_daily_loss_pct']*100:.1f}%"
                    )
                    return False
        except Exception:
            # If we can't fetch, do not block by default
            pass
        
        return True

    def _estimate_symbol_category(self, symbol: str) -> str:
        """Heuristic classification using price/vol + optional advanced factors if available."""
        try:
            # Price heuristic
            snapshot = self.alpaca.get_snapshot(symbol, feed='iex')
            price = float(snapshot.latest_trade.price) if snapshot and snapshot.latest_trade else 0
            # Volatility heuristic
            bars = self.alpaca.get_bars(symbol, '1Day', limit=30, feed='iex').df
            vol_pct = float(bars['close'].pct_change().std() * 100) if not bars.empty else 0
            # Volume
            volume = float(snapshot.daily_bar.volume) if snapshot and snapshot.daily_bar else 0
            # Enrich with free data
            finnhub = fetch_finnhub_profile(symbol)
            yf_snap = fetch_yf_snapshot(symbol)
            yf_opt = fetch_yf_options_summary(symbol)
            additional = {
                'market_cap': finnhub.get('market_cap'),
                'beta': finnhub.get('beta'),
                'short_interest_pct': yf_snap.get('short_percent_float'),
                'unusual_options_activity': True if (yf_opt.get('call_put_ratio', 0) > 2 and yf_opt.get('total_volume', 0) > 50_000) else False,
                'catalyst_type': 'earnings'  # placeholder; could set from context
            }
            category, _conf = categorize_symbol_advanced(
                symbol=symbol,
                price=price or (yf_snap.get('price') or 0),
                volume=volume or (yf_snap.get('average_volume') or 0),
                additional_data=additional
            )
            return category
        except Exception:
            pass
        return 'conservative'

    def _current_category_exposure(self, category: str) -> float:
        """Sum market value of positions by category using current prices."""
        try:
            positions = self.alpaca.list_positions()
            total = 0.0
            for p in positions:
                sym = p.symbol
                cat = self._category_by_symbol.get(sym) or self._estimate_symbol_category(sym)
                if cat == category:
                    total += float(p.market_value)
            return total
        except Exception:
            return 0.0
    
    async def _execute_management(self, position, gpt_decision: str):
        """Execute position management decision from GPT-5"""
        # Parse and execute management decision
        pass
    
    def _format_trades_for_analysis(self, trades) -> str:
        """Format trades for GPT-5 analysis"""
        # Format trade history for learning
        return "Trade history formatted here"


async def main():
    """
    Main autonomous trading loop
    """
    # Initialize the GPT-5 trading brain
    trading_brain = GPT5TradingBrain()
    
    logger.info("🚀 GPT-5 Autonomous Trading System Started")
    logger.info("Target: 10x returns in 3 months")
    
    while True:
        try:
            # Check if market is open
            clock = trading_brain.alpaca.get_clock()
            
            if not clock.is_open:
                logger.info("Market closed, waiting...")
                await asyncio.sleep(300)  # Check every 5 minutes
                continue
            
            # 1. GPT-5 scans for opportunities
            logger.info("🔍 GPT-5 scanning market...")
            opportunities = await trading_brain.autonomous_market_scan()
            
            # 2. Deep analysis on top opportunities
            for opp in opportunities[:3]:  # Top 3
                symbol = opp['symbol']
                logger.info(f"🧠 GPT-5 analyzing {symbol}...")
                
                analysis = await trading_brain.deep_analysis(symbol)
                
                if analysis['decision'] == 'GO':
                    # 3. Execute trade
                    trade_plan = {
                        'symbol': symbol,
                        'confidence': analysis['confidence'],
                        'position_size_pct': analysis['position_size_pct'],
                        'entry_price': analysis['entry_price'],
                        'stop_loss': analysis['stop_loss'],
                        'target_1': analysis['target_1'],
                        'reasoning': analysis['reasoning']
                    }
                    
                    await trading_brain.execute_trade(trade_plan)
            
            # 4. Manage existing positions
            await trading_brain.manage_positions()
            
            # 5. Learn and adapt (run every hour)
            if datetime.now().minute == 0:
                await trading_brain.learn_and_adapt()
            
            # Dynamic sleep based on market conditions
            await asyncio.sleep(30)  # Check every 30 seconds during market hours
            
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            await asyncio.sleep(60)


if __name__ == "__main__":
    # Set up environment variables
    print("""
    ================================
    GPT-5 TRADING SYSTEM SETUP
    ================================
    
    Required environment variables in .env:
    
    OPENAI_API_KEY=sk-...          # Your OpenAI API key
    TAVILY_API_KEY=tvly-...        # Tavily for web search (optional)
    ALPACA_API_KEY=PK...           # Your Alpaca API key
    ALPACA_SECRET_KEY=...          # Your Alpaca secret
    ALPACA_BASE_URL=https://paper-api.alpaca.markets
    
    Once configured, the system will:
    1. Use GPT-5 to scan the entire market
    2. Find opportunities before humans
    3. Execute trades automatically
    4. Learn and improve continuously
    
    Starting autonomous trading...
    """)
    
    # Run the autonomous trading system
    asyncio.run(main())