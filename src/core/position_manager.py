#!/usr/bin/env python3
"""
position_manager.py - Monitors open positions and executes exit strategies
This is the CRITICAL missing piece - handles stop losses, take profits, and trailing stops
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import alpaca_trade_api as tradeapi
import os
from loguru import logger
import pandas as pd
from dataclasses import dataclass

@dataclass
class PositionTarget:
    """Track targets for each position"""
    symbol: str
    entry_price: float
    stop_loss: float
    take_profit_1: float  # First target (sell 25%)
    take_profit_2: float  # Second target (sell 50%)
    take_profit_3: float  # Final target (sell 25%)
    trailing_stop_active: bool = False
    highest_price: float = 0
    partial_exits: Dict = None

class PositionManager:
    """
    Manages all open positions - monitors and exits at the right time
    This is what makes or breaks profitability!
    """
    
    def __init__(self, api: tradeapi.REST, db=None):
        self.api = api
        self.db = db
        
        # Track position targets
        self.position_targets = {}
        
        # Exit strategy parameters (configurable via env)
        stop_loss_pct = float(os.getenv('STOP_LOSS_PERCENT', 0.03))
        take_profit_1_pct = float(os.getenv('TAKE_PROFIT_PERCENT', 0.05))
        take_profit_2_pct = float(os.getenv('TAKE_PROFIT_2_PERCENT', 0.10))
        take_profit_3_pct = float(os.getenv('TAKE_PROFIT_3_PERCENT', 0.15))
        trailing_stop_pct = float(os.getenv('TRAILING_STOP_PERCENT', 0.02))
        time_stop_minutes = int(float(os.getenv('TIME_STOP_MINUTES', 180)))

        self.exit_config = {
            'stop_loss_pct': stop_loss_pct,
            'take_profit_1_pct': take_profit_1_pct,
            'take_profit_2_pct': take_profit_2_pct,
            'take_profit_3_pct': take_profit_3_pct,
            'trailing_stop_pct': trailing_stop_pct,
            'time_stop_minutes': time_stop_minutes,
        }
        
        # Track entry times for time stops
        self.entry_times = {}
        
        logger.info("Position Manager initialized")
    
    def add_position(self, symbol: str, entry_price: float, 
                     stop_loss: Optional[float] = None,
                     take_profit: Optional[float] = None,
                     strategy_type: str = "standard"):
        """
        Add a new position to monitor
        Called when bot enters a position
        """
        # Calculate targets based on strategy
        if strategy_type == "aggressive":
            # Wider stops, bigger targets for volatile stocks
            stop = entry_price * 0.95  # 5% stop
            tp1 = entry_price * 1.10   # 10% first target
            tp2 = entry_price * 1.20   # 20% second
            tp3 = entry_price * 1.30   # 30% moonshot
        elif strategy_type == "scalp":
            # Tight stops, quick profits
            stop = entry_price * 0.98   # 2% stop
            tp1 = entry_price * 1.03    # 3% first target
            tp2 = entry_price * 1.05    # 5% second
            tp3 = entry_price * 1.07    # 7% final
        else:  # standard
            stop = stop_loss or entry_price * (1 - self.exit_config['stop_loss_pct'])
            tp1 = take_profit or entry_price * (1 + self.exit_config['take_profit_1_pct'])
            tp2 = entry_price * (1 + self.exit_config['take_profit_2_pct'])
            tp3 = entry_price * (1 + self.exit_config['take_profit_3_pct'])
        
        self.position_targets[symbol] = PositionTarget(
            symbol=symbol,
            entry_price=entry_price,
            stop_loss=stop,
            take_profit_1=tp1,
            take_profit_2=tp2,
            take_profit_3=tp3,
            highest_price=entry_price,
            partial_exits={'tp1': False, 'tp2': False, 'tp3': False}
        )
        
        self.entry_times[symbol] = datetime.now()
        
        logger.info(f"Added position monitor for {symbol}")
        logger.info(f"  Entry: ${entry_price:.2f}")
        logger.info(f"  Stop: ${stop:.2f} ({(stop/entry_price - 1)*100:.1f}%)")
        logger.info(f"  TP1: ${tp1:.2f} (+{(tp1/entry_price - 1)*100:.1f}%)")
        logger.info(f"  TP2: ${tp2:.2f} (+{(tp2/entry_price - 1)*100:.1f}%)")
        logger.info(f"  TP3: ${tp3:.2f} (+{(tp3/entry_price - 1)*100:.1f}%)")
    
    async def monitor_positions(self):
        """
        Main monitoring loop - checks all positions every 10 seconds
        This is the heart of the exit strategy
        """
        while True:
            try:
                # Get all open positions
                positions = self.api.list_positions()
                
                if not positions:
                    await asyncio.sleep(10)
                    continue
                
                for position in positions:
                    await self._check_position(position)
                
                # Clean up closed positions from tracking
                open_symbols = {p.symbol for p in positions}
                closed = [s for s in self.position_targets.keys() if s not in open_symbols]
                for symbol in closed:
                    del self.position_targets[symbol]
                    if symbol in self.entry_times:
                        del self.entry_times[symbol]
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Error monitoring positions: {e}")
                await asyncio.sleep(10)
    
    async def _check_position(self, position):
        """
        Check a single position for exit conditions
        """
        symbol = position.symbol
        current_price = float(position.current_price)
        qty = int(position.qty)
        unrealized_pl_pct = float(position.unrealized_plpc)
        
        # Get or create targets
        if symbol not in self.position_targets:
            # Position was opened before bot started
            entry_price = float(position.avg_entry_price)
            self.add_position(symbol, entry_price)
        
        target = self.position_targets[symbol]
        
        # Update highest price for trailing stop
        if current_price > target.highest_price:
            target.highest_price = current_price
            
            # Activate trailing stop after first target hit
            if current_price >= target.take_profit_1:
                target.trailing_stop_active = True
        
        # Log current status
        pl_display = "🟢" if unrealized_pl_pct >= 0 else "🔴"
        logger.debug(f"{pl_display} {symbol}: ${current_price:.2f} ({unrealized_pl_pct:+.1f}%)")
        
        # CHECK 1: Stop Loss
        if current_price <= target.stop_loss:
            logger.warning(f"⛔ STOP LOSS HIT: {symbol} at ${current_price:.2f}")
            await self._exit_position(symbol, qty, "STOP_LOSS")
            return
        
        # CHECK 2: Trailing Stop (if active)
        if target.trailing_stop_active:
            trailing_stop = target.highest_price * (1 - self.exit_config['trailing_stop_pct'])
            if current_price <= trailing_stop:
                logger.info(f"📉 TRAILING STOP HIT: {symbol} at ${current_price:.2f}")
                logger.info(f"  Highest: ${target.highest_price:.2f}, Stop: ${trailing_stop:.2f}")
                await self._exit_position(symbol, qty, "TRAILING_STOP")
                return
        
        # CHECK 3: Take Profit Levels (scaling out)
        
        # First target - sell 25%
        if current_price >= target.take_profit_1 and not target.partial_exits['tp1']:
            qty_to_sell = max(1, int(qty * 0.25))
            logger.info(f"🎯 TARGET 1 HIT: {symbol} at ${current_price:.2f}")
            await self._partial_exit(symbol, qty_to_sell, "TAKE_PROFIT_1")
            target.partial_exits['tp1'] = True
        
        # Second target - sell 50% of remaining
        if current_price >= target.take_profit_2 and not target.partial_exits['tp2']:
            qty_to_sell = max(1, int(qty * 0.50))
            logger.info(f"🎯 TARGET 2 HIT: {symbol} at ${current_price:.2f}")
            await self._partial_exit(symbol, qty_to_sell, "TAKE_PROFIT_2")
            target.partial_exits['tp2'] = True
        
        # Third target - sell remaining
        if current_price >= target.take_profit_3 and not target.partial_exits['tp3']:
            logger.info(f"🎯 TARGET 3 HIT: {symbol} at ${current_price:.2f}")
            await self._exit_position(symbol, qty, "TAKE_PROFIT_3")
            return
        
        # CHECK 4: Time Stop (exit if position is stale)
        if symbol in self.entry_times:
            time_held = (datetime.now() - self.entry_times[symbol]).seconds / 60
            if time_held > self.exit_config['time_stop_minutes'] and abs(unrealized_pl_pct) < 0.02:
                logger.info(f"⏰ TIME STOP: {symbol} flat after {time_held:.0f} minutes")
                await self._exit_position(symbol, qty, "TIME_STOP")
                return
    
    async def _exit_position(self, symbol: str, qty: int, reason: str):
        """
        Exit entire position
        """
        try:
            order = self.api.submit_order(
                symbol=symbol,
                qty=qty,
                side='sell',
                type='market',
                time_in_force='day'
            )
            
            logger.info(f"✅ EXIT ORDER PLACED: {symbol} x{qty} ({reason})")
            logger.info(f"  Order ID: {order.id}")
            
            # Log to database if available
            if self.db:
                self.db.log_exit(symbol, qty, reason)
            
            # Remove from tracking
            if symbol in self.position_targets:
                del self.position_targets[symbol]
            if symbol in self.entry_times:
                del self.entry_times[symbol]
                
        except Exception as e:
            logger.error(f"Failed to exit {symbol}: {e}")
    
    async def _partial_exit(self, symbol: str, qty: int, reason: str):
        """
        Partial exit (scaling out)
        """
        try:
            if qty < 1:
                return
                
            order = self.api.submit_order(
                symbol=symbol,
                qty=qty,
                side='sell',
                type='market',
                time_in_force='day'
            )
            
            logger.info(f"✅ PARTIAL EXIT: {symbol} x{qty} ({reason})")
            
            # Log to database if available
            if self.db:
                self.db.log_partial_exit(symbol, qty, reason)
                
        except Exception as e:
            logger.error(f"Failed partial exit {symbol}: {e}")
    
    async def emergency_exit_all(self):
        """
        Emergency exit all positions (e.g., end of day, max loss hit)
        """
        logger.warning("🚨 EMERGENCY EXIT - Closing all positions")
        
        positions = self.api.list_positions()
        
        for position in positions:
            try:
                order = self.api.submit_order(
                    symbol=position.symbol,
                    qty=int(position.qty),
                    side='sell',
                    type='market',
                    time_in_force='day'
                )
                logger.info(f"Emergency exit: {position.symbol}")
            except Exception as e:
                logger.error(f"Failed to exit {position.symbol}: {e}")
    
    def get_position_summary(self) -> Dict:
        """
        Get summary of all positions and their status
        """
        positions = self.api.list_positions()
        
        summary = {
            'total_positions': len(positions),
            'total_value': 0,
            'total_pl': 0,
            'positions': []
        }
        
        for position in positions:
            symbol = position.symbol
            current_price = float(position.current_price)
            unrealized_pl = float(position.unrealized_pl)
            unrealized_pl_pct = float(position.unrealized_plpc)
            
            pos_data = {
                'symbol': symbol,
                'qty': int(position.qty),
                'current_price': current_price,
                'entry_price': float(position.avg_entry_price),
                'pl': unrealized_pl,
                'pl_pct': unrealized_pl_pct,
                'value': float(position.market_value)
            }
            
            # Add target info if available
            if symbol in self.position_targets:
                target = self.position_targets[symbol]
                pos_data['stop_loss'] = target.stop_loss
                pos_data['next_target'] = self._get_next_target(target, current_price)
                pos_data['highest'] = target.highest_price
                pos_data['trailing_active'] = target.trailing_stop_active
            
            summary['positions'].append(pos_data)
            summary['total_value'] += pos_data['value']
            summary['total_pl'] += unrealized_pl
        
        return summary
    
    def _get_next_target(self, target: PositionTarget, current_price: float) -> float:
        """Get the next price target"""
        if not target.partial_exits['tp1']:
            return target.take_profit_1
        elif not target.partial_exits['tp2']:
            return target.take_profit_2
        elif not target.partial_exits['tp3']:
            return target.take_profit_3
        else:
            return 0  # All targets hit


# Integration with your main bot
class TradingBotWithExits:
    """
    Example of how to integrate the PositionManager with your bot
    """
    
    def __init__(self, api, scanner, strategy):
        self.api = api
        self.scanner = scanner
        self.strategy = strategy
        self.position_manager = PositionManager(api)
    
    async def run(self):
        """
        Main bot loop with position monitoring
        """
        # Start position monitor in background
        monitor_task = asyncio.create_task(self.position_manager.monitor_positions())
        
        try:
            while True:
                # Your existing logic to find and enter trades
                signals = await self.scanner.get_trade_signals()
                
                for signal in signals:
                    if self.should_enter(signal):
                        # Place buy order
                        order = await self.place_buy_order(signal)
                        
                        # Add to position manager for monitoring
                        if order:
                            self.position_manager.add_position(
                                symbol=signal['symbol'],
                                entry_price=signal['entry_price'],
                                stop_loss=signal.get('stop_loss'),
                                take_profit=signal.get('target_1'),
                                strategy_type=signal.get('strategy_type', 'standard')
                            )
                
                # Show current positions
                summary = self.position_manager.get_position_summary()
                if summary['total_positions'] > 0:
                    logger.info(f"Open positions: {summary['total_positions']}, "
                              f"P&L: ${summary['total_pl']:.2f}")
                
                await asyncio.sleep(60)  # Main loop interval
                
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            # Clean exit
            await self.position_manager.emergency_exit_all()
            monitor_task.cancel()


# Standalone testing
async def test_position_manager():
    """Test the position manager"""
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    api = tradeapi.REST(
        os.getenv('ALPACA_API_KEY'),
        os.getenv('ALPACA_SECRET_KEY'),
        os.getenv('ALPACA_BASE_URL')
    )
    
    manager = PositionManager(api)
    
    # Check current positions
    summary = manager.get_position_summary()
    
    print("\n📊 CURRENT POSITIONS 📊\n")
    
    if summary['total_positions'] == 0:
        print("No open positions")
    else:
        for pos in summary['positions']:
            print(f"{pos['symbol']}:")
            print(f"  Qty: {pos['qty']}")
            print(f"  Entry: ${pos['entry_price']:.2f}")
            print(f"  Current: ${pos['current_price']:.2f}")
            print(f"  P&L: ${pos['pl']:.2f} ({pos['pl_pct']:+.1f}%)")
            if 'next_target' in pos and pos['next_target'] > 0:
                print(f"  Next Target: ${pos['next_target']:.2f}")
            print()
        
        print(f"Total P&L: ${summary['total_pl']:.2f}")
    
    # Start monitoring
    print("\n Starting position monitor...")
    print("Press Ctrl+C to stop\n")
    
    await manager.monitor_positions()


if __name__ == "__main__":
    asyncio.run(test_position_manager())