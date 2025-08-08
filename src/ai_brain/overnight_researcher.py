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
    Watchlist persists and improves throughout the night
    """
    
    def __init__(self, trading_brain):
        self.brain = trading_brain
        self.watchlist = []  # Max 6 stocks - PERSISTS all night
        self.max_watchlist_size = 6
        self.research_history = {}  # Track how deeply we've researched each stock
        self.confidence_threshold = 70  # Minimum confidence to make the list (lowered to allow growth)
        self.cycle_count = 0  # Track how many cycles we've done
        self.last_reset_hour = None  # Track when we last reset (new day)
        
        # Balance between deepening vs discovering (changes through the night)
        self.discovery_energy = 0.5  # Start with 50/50 balance
        self.removed_stocks = []  # Track what we've already rejected tonight
        
    async def overnight_research_cycle(self) -> List[Dict]:
        """
        Main overnight research cycle - builds on previous cycles
        Returns updated watchlist with confidence scores
        """
        self.cycle_count += 1
        current_hour = datetime.now().hour
        
        # Reset watchlist at midnight for new trading day
        if current_hour == 0 and self.last_reset_hour != 0:
            logger.info("🔄 Midnight reset - Starting fresh for new trading day")
            self.reset_for_new_day()
        self.last_reset_hour = current_hour
        
        logger.info(f"🌙 Overnight research cycle #{self.cycle_count}")
        logger.info(f"📊 Current watchlist: {len(self.watchlist)}/{self.max_watchlist_size} stocks")
        
        # Adjust discovery vs deepening balance based on time and list status
        hours_until_open = self._hours_until_market_open()
        list_completeness = len(self.watchlist) / self.max_watchlist_size
        
        # More discovery early in night, more deepening as morning approaches
        if hours_until_open > 6:
            self.discovery_energy = 0.7 if list_completeness < 0.8 else 0.3
        elif hours_until_open > 3:
            self.discovery_energy = 0.5 if list_completeness < 1.0 else 0.2
        else:
            self.discovery_energy = 0.3 if list_completeness < 1.0 else 0.1
        
        logger.info(f"⚖️ Research balance: {int(self.discovery_energy*100)}% discovery, {int((1-self.discovery_energy)*100)}% deepening")
        
        # Step 1: Deepen existing watchlist (use portion of energy)
        if self.watchlist and self.discovery_energy < 1.0:
            logger.info(f"🔬 Deepening research on existing {len(self.watchlist)} stocks")
            self.watchlist = await self._deep_research_watchlist()
        
        # Step 2: Discover new opportunities (use portion of energy)
        if self.discovery_energy > 0 and len(self.watchlist) < self.max_watchlist_size:
            slots_available = self.max_watchlist_size - len(self.watchlist)
            logger.info(f"🔍 Searching for {slots_available} new opportunities")
            
            new_opportunities = await self._discover_opportunities()
            
            # Add new opportunities that aren't in removed list
            for opp in new_opportunities:
                symbol = opp['symbol']
                if symbol not in self.removed_stocks and len(self.watchlist) < self.max_watchlist_size:
                    # Check if already in watchlist
                    if not any(stock['symbol'] == symbol for stock in self.watchlist):
                        if opp.get('confidence', 0) >= self.confidence_threshold:
                            opp['discovered_cycle'] = self.cycle_count
                            opp['research_depth'] = 1
                            self.watchlist.append(opp)
                            self.research_history[symbol] = 1
                            logger.info(f"✅ Added {symbol} to watchlist (Confidence: {opp['confidence']}%)")
        
        # Step 3: Optimize - remove low confidence, keep building toward 6
        self.watchlist = await self._optimize_watchlist()
        
        # Step 4: Show current status
        self._show_watchlist_status()
        
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
        Preserves all previous findings and builds on them
        """
        updated_watchlist = []
        
        for stock in self.watchlist:
            symbol = stock['symbol']
            research_depth = stock.get('research_depth', 1)
            
            # Compile all previous findings
            previous_findings = stock.get('research_notes', [])
            findings_summary = "\n".join([f"- Cycle {f['cycle']}: {f['finding']}" for f in previous_findings[-5:]])
            
            # Deeper research based on how many times we've looked at it
            research_prompt = f"""
            DEEP RESEARCH - Level {research_depth + 1} Analysis
            
            Stock: {symbol}
            Current confidence: {stock.get('confidence', 0)}%
            Original catalyst: {stock.get('catalyst', 'Unknown')}
            Discovered in cycle: {stock.get('discovered_cycle', 0)}
            Research depth: {research_depth}
            
            Previous findings:
            {findings_summary}
            
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
                
                # Update stock info while preserving history
                old_confidence = stock['confidence']
                stock['confidence'] = analysis.get('confidence', stock['confidence'])
                stock['updated_analysis'] = analysis.get('reasoning', '')
                stock['research_depth'] = research_depth + 1
                
                # Add new finding to research notes
                if 'research_notes' not in stock:
                    stock['research_notes'] = []
                
                new_finding = {
                    'cycle': self.cycle_count,
                    'finding': analysis.get('reasoning', '')[:200],
                    'confidence_change': stock['confidence'] - old_confidence,
                    'depth': research_depth + 1
                }
                stock['research_notes'].append(new_finding)
                
                # Keep all context from previous cycles
                stock['last_updated_cycle'] = self.cycle_count
                
                self.research_history[symbol] = research_depth + 1
                
                if stock['confidence'] >= self.confidence_threshold - 5:  # Give stocks a chance
                    updated_watchlist.append(stock)
                    logger.info(f"  {symbol}: Confidence {stock['confidence']}% ({'+' if stock['confidence'] > old_confidence else ''}{stock['confidence'] - old_confidence}%) - Depth {research_depth + 1}")
                else:
                    self.removed_stocks.append(symbol)
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
    
    def _hours_until_market_open(self) -> float:
        """Calculate hours until market opens (9:30 AM ET)"""
        now = datetime.now()
        market_open = now.replace(hour=9, minute=30, second=0)
        
        # If past 9:30 AM, calculate for next day
        if now.hour >= 9 and now.minute >= 30:
            market_open += timedelta(days=1)
        
        hours = (market_open - now).total_seconds() / 3600
        return max(0, hours)
    
    def _show_watchlist_status(self):
        """Show current watchlist status with details"""
        if not self.watchlist:
            logger.warning("⚠️ Watchlist empty - searching for opportunities")
            return
        
        logger.info("=" * 60)
        logger.info(f"📋 WATCHLIST STATUS - Cycle #{self.cycle_count}")
        logger.info("=" * 60)
        
        # Sort by confidence
        self.watchlist.sort(key=lambda x: x.get('confidence', 0), reverse=True)
        
        for i, stock in enumerate(self.watchlist, 1):
            confidence = stock.get('confidence', 0)
            depth = stock.get('research_depth', 1)
            discovered = stock.get('discovered_cycle', 0)
            
            # Show confidence trend
            if stock.get('research_notes'):
                recent_changes = [n['confidence_change'] for n in stock['research_notes'][-3:]]
                trend = "📈" if sum(recent_changes) > 0 else "📉" if sum(recent_changes) < 0 else "➡️"
            else:
                trend = "🆕"
            
            logger.info(f"{i}. {stock['symbol']} {trend} - {confidence}% confidence")
            logger.info(f"   Catalyst: {stock.get('catalyst', 'N/A')[:60]}")
            logger.info(f"   Research: Depth {depth} | Added cycle {discovered} | Updated cycle {stock.get('last_updated_cycle', discovered)}")
        
        avg_confidence = sum(s.get('confidence', 0) for s in self.watchlist) / len(self.watchlist)
        logger.info("=" * 60)
        logger.info(f"Average confidence: {avg_confidence:.1f}%")
        logger.info(f"Hours until market: {self._hours_until_market_open():.1f}h")
        logger.info("=" * 60)
    
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
    
    def reset_for_new_day(self):
        """
        Reset for a new trading day (called at midnight)
        """
        self.watchlist = []
        self.research_history = {}
        self.removed_stocks = []
        self.cycle_count = 0
        self.discovery_energy = 0.5
        logger.info("🔄 Reset for new trading day - starting fresh")
    
    def clear_watchlist(self):
        """
        Clear the watchlist (call after market opens and positions are taken)
        """
        # Save best performers for learning
        if self.watchlist:
            top_picks = [s['symbol'] for s in self.watchlist[:3]]
            logger.info(f"📝 Today's top picks were: {', '.join(top_picks)}")
        
        self.watchlist = []
        self.research_history = {}
        self.removed_stocks = []
        logger.info("Watchlist cleared after market open execution")