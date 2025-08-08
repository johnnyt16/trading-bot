#!/usr/bin/env python3
"""
Overnight Research System - Builds high-confidence watchlist for market open
Continuously refines a list of 6 top opportunities while market is closed
"""

import json
from typing import Dict, List
from datetime import datetime, timedelta
from loguru import logger

class OvernightResearcher:
    """
    Manages overnight research and watchlist building
    Goal: Have 6 HIGH-CONFIDENCE stocks ready at market open
    """
    
    def __init__(self, trading_brain):
        self.brain = trading_brain
        self.watchlist = []  # Max 6 stocks
        self.max_watchlist_size = 6
        self.research_history = {}  # Track how deeply we've researched each stock
        self.confidence_threshold = 75  # Minimum confidence to make the list
        
    async def overnight_research_cycle(self) -> List[Dict]:
        """
        Main overnight research cycle
        Returns updated watchlist with confidence scores
        """
        logger.info("🌙 Starting overnight research cycle")
        
        # Step 1: Determine research focus based on watchlist status
        current_count = len(self.watchlist)
        needs_discovery = current_count < self.max_watchlist_size
        
        if needs_discovery:
            logger.info(f"📊 Watchlist has {current_count}/{self.max_watchlist_size} stocks - DISCOVERING NEW")
            # Find new opportunities
            new_opportunities = await self._discover_opportunities()
            
            # Add best new opportunities to watchlist
            for opp in new_opportunities:
                if len(self.watchlist) < self.max_watchlist_size:
                    if opp.get('confidence', 0) >= self.confidence_threshold:
                        self.watchlist.append(opp)
                        self.research_history[opp['symbol']] = 1
                        logger.info(f"✅ Added {opp['symbol']} to watchlist (Confidence: {opp['confidence']}%)")
        
        # Step 2: Deep dive on existing watchlist
        if self.watchlist:
            logger.info(f"🔬 Deep researching {len(self.watchlist)} watchlist stocks")
            self.watchlist = await self._deep_research_watchlist()
        
        # Step 3: Rank and potentially replace low-confidence stocks
        self.watchlist = await self._optimize_watchlist()
        
        # Step 4: Prepare final pre-market analysis
        self._prepare_market_open_strategy()
        
        return self.watchlist
    
    async def _discover_opportunities(self) -> List[Dict]:
        """
        Discover new opportunities for the watchlist
        Focus on tomorrow's catalysts
        """
        discovery_prompt = f"""
        OVERNIGHT DISCOVERY MODE - Find tomorrow's best opportunities
        
        Current time: {datetime.now().strftime('%H:%M')} (overnight)
        Target: Find stocks that will move 5-20% at market open
        
        Search for:
        1. Earnings releases after close today or before open tomorrow
        2. FDA decisions due tomorrow
        3. Major news breaking overnight (Asia/Europe affecting US)
        4. Unusual after-hours volume or price moves
        5. Social media momentum building (Reddit/Twitter viral stocks)
        6. Technical setups completing (about to break resistance)
        7. Sector sympathy plays (if NVDA reports well, AMD benefits)
        
        Focus on:
        - HIGH PROBABILITY moves (not speculation)
        - LIQUID stocks (no penny stocks)
        - CLEAR CATALYSTS within 24 hours
        - Risk/reward > 1:3
        
        Return top opportunities with confidence scores.
        """
        
        # Use the brain's market scan in research mode
        opportunities = await self.brain.autonomous_market_scan(research_mode=True)
        
        # Filter for high confidence only
        filtered = [opp for opp in opportunities if opp.get('confidence', 0) >= self.confidence_threshold]
        
        return filtered[:3]  # Return top 3 to avoid overwhelming
    
    async def _deep_research_watchlist(self) -> List[Dict]:
        """
        Perform deeper research on existing watchlist stocks
        """
        updated_watchlist = []
        
        for stock in self.watchlist:
            symbol = stock['symbol']
            research_depth = self.research_history.get(symbol, 0)
            
            # Deeper research based on how many times we've looked at it
            research_prompt = f"""
            DEEP RESEARCH - Level {research_depth + 1} Analysis
            
            Stock: {symbol}
            Previous confidence: {stock.get('confidence', 0)}%
            Original catalyst: {stock.get('catalyst', 'Unknown')}
            
            Perform {"DEEPER" if research_depth > 0 else "INITIAL"} research:
            
            Level 1 (Basic):
            - Verify catalyst is still valid
            - Check after-hours price action
            - Latest news updates
            
            Level 2 (Deeper):
            - Insider trading activity
            - Options flow analysis
            - Institutional ownership changes
            - Technical indicators (RSI, MACD, Volume)
            
            Level 3 (Deepest):
            - Comparable company analysis
            - Historical reaction to similar catalysts
            - Risk factors and downside scenarios
            - Exact entry/exit strategy
            
            Current research level: {research_depth + 1}
            
            Update confidence score based on findings.
            If confidence drops below {self.confidence_threshold}%, flag for removal.
            
            Return updated analysis with new confidence score.
            """
            
            try:
                # Search for latest updates on this stock
                latest_search = self.brain.tavily.search(
                    f"{symbol} stock latest news after hours {datetime.now().strftime('%B %d')}",
                    max_results=3
                )
                
                # Get GPT's updated analysis
                response = await self.brain.client.chat.completions.create(
                    model=self.brain.model,
                    messages=[
                        {"role": "system", "content": self.brain.system_prompt},
                        {"role": "user", "content": research_prompt + f"\n\nLatest info: {json.dumps(latest_search.get('results', [])[:2])}"}
                    ],
                    temperature=0.3,
                    max_tokens=1000
                )
                
                # Parse updated confidence
                analysis = self.brain._parse_json_response(response.choices[0].message.content)
                
                # Update stock info
                stock['confidence'] = analysis.get('confidence', stock['confidence'])
                stock['updated_analysis'] = analysis.get('reasoning', '')
                stock['research_depth'] = research_depth + 1
                
                self.research_history[symbol] = research_depth + 1
                
                if stock['confidence'] >= self.confidence_threshold:
                    updated_watchlist.append(stock)
                    logger.info(f"  {symbol}: Updated confidence {stock['confidence']}% (depth: {research_depth + 1})")
                else:
                    logger.warning(f"  {symbol}: Removed - confidence dropped to {stock['confidence']}%")
                    
            except Exception as e:
                logger.error(f"Failed to research {symbol}: {e}")
                updated_watchlist.append(stock)  # Keep it if research fails
        
        return updated_watchlist
    
    async def _optimize_watchlist(self) -> List[Dict]:
        """
        Optimize the watchlist - keep only the best 6
        Try to find better replacements for low-confidence stocks
        """
        # Sort by confidence
        self.watchlist.sort(key=lambda x: x.get('confidence', 0), reverse=True)
        
        # If we have more than 6, keep only top 6
        if len(self.watchlist) > self.max_watchlist_size:
            removed = self.watchlist[self.max_watchlist_size:]
            self.watchlist = self.watchlist[:self.max_watchlist_size]
            for stock in removed:
                logger.info(f"  Removed {stock['symbol']} from watchlist (lower priority)")
        
        # If we have less than 6, try to find more
        if len(self.watchlist) < self.max_watchlist_size:
            logger.info(f"  Watchlist has {len(self.watchlist)}/{self.max_watchlist_size} - seeking more opportunities")
            
            # Look for one more opportunity
            new_opportunities = await self._discover_opportunities()
            for opp in new_opportunities:
                if len(self.watchlist) < self.max_watchlist_size:
                    # Check if it's better than our worst stock
                    if self.watchlist and opp.get('confidence', 0) > self.watchlist[-1].get('confidence', 0):
                        # Replace the worst one
                        logger.info(f"  Replacing {self.watchlist[-1]['symbol']} with {opp['symbol']}")
                        self.watchlist[-1] = opp
                        self.watchlist.sort(key=lambda x: x.get('confidence', 0), reverse=True)
                    elif len(self.watchlist) < self.max_watchlist_size:
                        self.watchlist.append(opp)
        
        return self.watchlist
    
    def _prepare_market_open_strategy(self):
        """
        Prepare final strategy for market open
        """
        if not self.watchlist:
            logger.warning("⚠️ No stocks in watchlist for market open")
            return
        
        logger.info("=" * 60)
        logger.info("🎯 MARKET OPEN STRATEGY - TOP 6 OPPORTUNITIES")
        logger.info("=" * 60)
        
        for i, stock in enumerate(self.watchlist, 1):
            logger.info(f"\n{i}. {stock['symbol']} - Confidence: {stock['confidence']}%")
            logger.info(f"   Catalyst: {stock.get('catalyst', 'N/A')[:80]}")
            logger.info(f"   Entry: ${stock.get('entry_price', 0):.2f}")
            logger.info(f"   Target: ${stock.get('target_1', 0):.2f} ({stock.get('target_move', 0):.1f}%)")
            logger.info(f"   Stop: ${stock.get('stop_loss', 0):.2f}")
            logger.info(f"   Research Depth: Level {stock.get('research_depth', 1)}")
        
        logger.info("=" * 60)
        logger.info(f"Ready to execute at market open with {len(self.watchlist)} high-confidence trades")
        logger.info("=" * 60)
    
    def get_top_opportunities(self, count: int = 3) -> List[Dict]:
        """
        Get the top N opportunities from watchlist
        """
        return self.watchlist[:count]
    
    def clear_watchlist(self):
        """
        Clear the watchlist (call after market opens and positions are taken)
        """
        self.watchlist = []
        self.research_history = {}
        logger.info("Watchlist cleared for new session")