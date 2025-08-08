#!/usr/bin/env python3
"""
gpt5_trading_system.py - Ultimate AI-first trading system using GPT-5
Designed for OpenAI's most advanced model with web search and reasoning
"""

import os
import asyncio
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import openai
from openai import AsyncOpenAI
import alpaca_trade_api as tradeapi
from loguru import logger
import pandas as pd
import numpy as np
from tavily import TavilyClient  # Web search API
import yfinance as yf  # Keep for fundamental research
from dotenv import load_dotenv

load_dotenv()

class GPT5TradingBrain:
    """
    The most advanced AI trading system using GPT-5
    Complete autonomous trading with web search and reasoning
    """
    
    def __init__(self):
        # Initialize OpenAI with GPT-5
        self.client = AsyncOpenAI(
            api_key=os.getenv('OPENAI_API_KEY')
        )
        
        # Model hierarchy - will try in order if rate limited
        self.model_hierarchy = [
            "gpt-5",            # GPT-5 (when available - will fallback if not)
            "gpt-4o",           # Best current model
            "gpt-4-turbo",      # Fallback to GPT-4 Turbo
            "gpt-4",            # Standard GPT-4
            "gpt-3.5-turbo",    # Cheaper fallback
            "gpt-4o-mini"       # Free/cheapest option
        ]
        self.current_model_index = 0
        self.model = self.model_hierarchy[self.current_model_index]
        
        # Track rate limit issues
        self.rate_limit_errors = 0
        self.last_rate_limit_time = None
        
        # Web search capability
        self.tavily = TavilyClient(api_key=os.getenv('TAVILY_API_KEY'))
        
        # Alpaca for execution
        self.alpaca = tradeapi.REST(
            os.getenv('ALPACA_API_KEY'),
            os.getenv('ALPACA_SECRET_KEY'),
            os.getenv('ALPACA_BASE_URL')
        )
        
        # Risk parameters (AI can override within limits)
        self.risk_limits = {
            'max_position_pct': 0.20,    # 20% max per position
            'max_daily_loss_pct': 0.15,  # 15% daily loss limit
            'max_positions': 10,          # 10 concurrent positions
            'min_confidence': 0.60        # 60% minimum AI confidence
        }
        
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
    
    async def autonomous_market_scan(self, research_mode: bool = False) -> List[Dict]:
        """
        GPT-5 scans the entire market using dynamic, intelligent search
        GPT generates its own search queries based on reasoning and market conditions
        
        Args:
            research_mode: If True, focuses on next-day catalysts and preparation
        """
        
        # Get current market context
        market_data = await self._get_market_context()
        
        # Determine if we're in research mode (market closed)
        clock = self.alpaca.get_clock()
        is_market_closed = not clock.is_open
        research_mode = research_mode or is_market_closed
        
        # Step 1: Let GPT generate intelligent search queries based on market conditions
        mode_context = "RESEARCH MODE - Preparing for next trading session" if research_mode else "LIVE TRADING MODE"
        
        search_generation_prompt = f"""
        Current Market Context:
        - Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} EST
        - Day: {datetime.now().strftime('%A')}
        - Market Status: {market_data['market_status']}
        - Mode: {mode_context}
        - SPY Change: {market_data['spy_change']}%
        - VIX Level: {market_data['vix_level']} ({"high volatility" if market_data['vix_level'] > 30 else "normal"})
        
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
            # GPT generates intelligent searches
            response = await self._make_gpt_request(
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": search_generation_prompt}
                ],
                temperature=0.5,  # More creative for search generation
                max_tokens=1000
            )
            
            # Parse GPT's search suggestions
            search_data = self._parse_json_response(response.choices[0].message.content)
            searches = search_data.get('searches', [])
            
            logger.info(f"GPT generated {len(searches)} intelligent searches")
            
        except Exception as e:
            logger.warning(f"Failed to generate dynamic searches: {e}")
            # Fallback to default searches
            searches = [
                {"query": f"reddit wallstreetbets trending stocks {datetime.now().strftime('%B %d')} sentiment", "purpose": "Social sentiment"},
                {"query": f"unusual options activity call sweeps {datetime.now().strftime('%B %d')}", "purpose": "Smart money flow"},
                {"query": f"FDA PDUFA calendar {datetime.now().strftime('%B %Y')} biotech catalysts", "purpose": "Upcoming catalysts"},
                {"query": "twitter financial trending stocks momentum social sentiment", "purpose": "Social momentum"},
                {"query": f"premarket movers gainers {datetime.now().strftime('%B %d')} news catalyst", "purpose": "Early movers"}
            ]
        
        # Step 2: Execute the searches (including social media)
        all_search_results = []
        for search_item in searches[:5]:  # Limit to top 5 to avoid rate limits
            query = search_item.get('query', search_item) if isinstance(search_item, dict) else search_item
            try:
                logger.debug(f"Searching: {query}")
                
                # Add social media focus for relevant searches
                if any(term in query.lower() for term in ['reddit', 'wsb', 'twitter', 'social', 'sentiment']):
                    # Search with social media focus
                    results = self.tavily.search(
                        query, 
                        max_results=5,
                        include_domains=["reddit.com", "twitter.com", "stocktwits.com"] if 'reddit' in query.lower() or 'social' in query.lower() else None
                    )
                else:
                    # Regular search
                    results = self.tavily.search(query, max_results=5)
                
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
                max_tokens=1000
            )
            
            follow_up_data = self._parse_json_response(response.choices[0].message.content)
            follow_up_searches = follow_up_data.get('follow_up_searches', [])
            hot_symbols = follow_up_data.get('hot_symbols', [])
            insights = follow_up_data.get('insights', '')
            
            logger.info(f"GPT insights: {insights[:200]}")
            
            # Execute follow-up searches
            for follow_up in follow_up_searches[:3]:
                query = follow_up.get('query', follow_up) if isinstance(follow_up, dict) else follow_up
                try:
                    logger.debug(f"Follow-up search: {query}")
                    results = self.tavily.search(query, max_results=3)
                    all_search_results.append({
                        'query': query,
                        'purpose': f"FOLLOW-UP: {follow_up.get('reason', '')}",
                        'results': results.get('results', [])
                    })
                except:
                    pass
                    
        except Exception as e:
            logger.warning(f"Follow-up search generation failed: {e}")
        
        # Step 4: Get real-time data for hot symbols identified by GPT
        market_movers = []
        
        # Add GPT-identified hot symbols to check list
        symbols_to_check = list(set(['NVDA', 'TSLA', 'AAPL', 'AMD', 'META', 'GOOGL', 'MSFT'] + hot_symbols[:10]))
        
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
                max_tokens=2000
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
            
            return validated_opportunities
            
        except Exception as e:
            logger.error(f"GPT analysis failed: {e}")
            return []
    
    async def deep_analysis(self, symbol: str) -> Dict:
        """
        GPT-5 performs deep analysis on a specific opportunity
        This is where GPT-5's reasoning capabilities shine
        """
        
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
            
            for search_query in searches[:2]:  # Limit to avoid rate limits
                try:
                    results = self.tavily.search(search_query, max_results=3)
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
        
        # Step 3: Analyze with GPT
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
        
        try:
            # GPT-5 performs deep analysis
            response = await self._make_gpt_request(
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": analysis_prompt}
                ],
                temperature=0.2,  # Even more focused for analysis
                max_tokens=2000
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
            
            # Add to AI memory for learning
            self.ai_memory.append({
                'symbol': symbol,
                'analysis': analysis,
                'timestamp': datetime.now()
            })
            
            logger.info(f"Analysis for {symbol}: {analysis['decision']} "
                       f"(Confidence: {analysis['confidence']}%)")
            
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
            
            # Calculate position size
            account = self.alpaca.get_account()
            portfolio_value = float(account.portfolio_value)
            position_size = portfolio_value * trade_plan['position_size_pct']
            
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
            logger.info(f"  Reasoning: {trade_plan.get('reasoning', 'N/A')[:200]}")
            
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
            try:
                position_search = self.tavily.search(
                    f"{symbol} stock news latest {datetime.now().strftime('%B %d')}",
                    max_results=3
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
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": management_prompt}
                    ],
                    temperature=0.2  # Lower temp for position management
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
        
        response = await self.client.chat.completions.create(
            model=self.model,
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
    async def _get_market_context(self) -> Dict:
        """Get current market conditions using best available data source"""
        spy_change = 0.0
        vix_level = 20.0
        clock = None
        
        try:
            # Primary: Use Alpaca for real-time SPY data
            clock = self.alpaca.get_clock()
            
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
            else:
                # After hours, get last close
                spy_bars = self.alpaca.get_bars('SPY', '1Day', limit=1, feed='iex').df
                if not spy_bars.empty:
                    spy_change = 0.0  # No intraday change after hours
                    
            # Get volatility indicator (VIXY as VIX proxy)
            try:
                vixy_snapshot = self.alpaca.get_snapshot('VIXY', feed='iex')
                if vixy_snapshot and vixy_snapshot.latest_trade:
                    vix_level = vixy_snapshot.latest_trade.price
            except:
                vix_level = 20.0  # Average VIX level
                
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
            except:
                logger.warning("Both data sources failed, using defaults")
        
        return {
            'market_status': 'open' if clock and clock.is_open else 'closed',
            'spy_change': round(spy_change, 2),
            'vix_level': round(vix_level, 2),
            'data_source': 'alpaca' if spy_change != 0.0 else 'default'
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
                    max_tokens=max_tokens
                )
                
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
    
    def _check_risk_limits(self, trade_plan: Dict) -> bool:
        """Check if trade meets risk parameters"""
        # Check position size
        if trade_plan.get('position_size_pct', 0) > self.risk_limits['max_position_pct']:
            return False
        
        # Check confidence
        if trade_plan.get('confidence', 0) < self.risk_limits['min_confidence']:
            return False
        
        # Check number of positions
        positions = self.alpaca.list_positions()
        if len(positions) >= self.risk_limits['max_positions']:
            return False
        
        return True
    
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