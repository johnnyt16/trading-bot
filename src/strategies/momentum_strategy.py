import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf
from ta.momentum import RSIIndicator
from ta.volume import VolumeWeightedAveragePrice
from loguru import logger
from src.core import Config, get_alpaca_client

class MomentumTradingBot:
    def __init__(self):
        self.api = get_alpaca_client()
        self.watchlist = Config.WATCHLIST
        self.positions = {}
        self.confidence_scores = {}
        
    def calculate_momentum_score(self, symbol):
        try:
            ticker = yf.Ticker(symbol)
            
            hist = ticker.history(period="1d", interval="1m")
            if hist.empty:
                return 0
            
            hist_5d = ticker.history(period="5d", interval="15m")
            
            score = 0
            confidence_factors = []
            
            current_price = hist['Close'].iloc[-1]
            avg_volume = hist_5d['Volume'].mean()
            current_volume = hist['Volume'].iloc[-1]
            
            if current_volume > avg_volume * 1.5:
                score += 0.25
                confidence_factors.append("High volume")
            
            rsi = RSIIndicator(hist['Close']).rsi().iloc[-1]
            if 30 < rsi < 40:  
                score += 0.25
                confidence_factors.append(f"RSI oversold: {rsi:.1f}")
            elif 60 < rsi < 70:  
                score += 0.15
                confidence_factors.append(f"RSI momentum: {rsi:.1f}")
            
            price_change_5min = (hist['Close'].iloc[-1] - hist['Close'].iloc[-6]) / hist['Close'].iloc[-6]
            if price_change_5min > 0.01:  
                score += 0.25
                confidence_factors.append(f"5min momentum: {price_change_5min*100:.2f}%")
            
            sma_20 = hist['Close'].rolling(window=20).mean().iloc[-1]
            if current_price > sma_20:
                score += 0.15
                confidence_factors.append("Above SMA20")
            
            logger.info(f"{symbol}: Score={score:.2f}, Factors={confidence_factors}")
            return score
            
        except Exception as e:
            logger.error(f"Error calculating momentum for {symbol}: {e}")
            return 0
    
    def should_enter_position(self, symbol):
        if symbol in self.positions:
            return False
            
        score = self.calculate_momentum_score(symbol)
        self.confidence_scores[symbol] = score
        
        return score >= Config.MIN_CONFIDENCE_SCORE
    
    def calculate_position_size(self):
        account = self.api.get_account()
        portfolio_value = float(account.portfolio_value)
        max_position = portfolio_value * Config.MAX_POSITION_SIZE
        return max_position
    
    def place_order(self, symbol, action='buy'):
        try:
            if action == 'buy':
                position_size = self.calculate_position_size()
                
                latest_trade = self.api.get_latest_trade(symbol)
                current_price = latest_trade.price
                
                qty = int(position_size / current_price)
                if qty < 1:
                    logger.warning(f"Position size too small for {symbol}")
                    return None
                
                order = self.api.submit_order(
                    symbol=symbol,
                    qty=qty,
                    side='buy',
                    type='market',
                    time_in_force='day'
                )
                
                logger.success(f"BUY order placed: {symbol} x{qty} @ ~${current_price:.2f}")
                
                stop_loss_price = current_price * (1 - Config.STOP_LOSS_PERCENT)
                self.api.submit_order(
                    symbol=symbol,
                    qty=qty,
                    side='sell',
                    type='stop',
                    time_in_force='gtc',
                    stop_price=stop_loss_price
                )
                logger.info(f"Stop loss set at ${stop_loss_price:.2f}")
                
                take_profit_price = current_price * (1 + Config.TAKE_PROFIT_PERCENT)
                self.api.submit_order(
                    symbol=symbol,
                    qty=qty,
                    side='sell',
                    type='limit',
                    time_in_force='gtc',
                    limit_price=take_profit_price
                )
                logger.info(f"Take profit set at ${take_profit_price:.2f}")
                
                self.positions[symbol] = {
                    'qty': qty,
                    'entry_price': current_price,
                    'stop_loss': stop_loss_price,
                    'take_profit': take_profit_price,
                    'timestamp': datetime.now()
                }
                
                return order
                
        except Exception as e:
            logger.error(f"Error placing {action} order for {symbol}: {e}")
            return None
    
    def check_market_hours(self):
        clock = self.api.get_clock()
        return clock.is_open
    
    def run_scanner(self):
        logger.info("Scanning for momentum opportunities...")
        
        for symbol in self.watchlist:
            if self.should_enter_position(symbol):
                logger.info(f"Signal detected for {symbol}! Confidence: {self.confidence_scores[symbol]:.2f}")
                self.place_order(symbol, 'buy')
            else:
                if symbol in self.confidence_scores:
                    logger.debug(f"{symbol}: Score {self.confidence_scores[symbol]:.2f} below threshold")
    
    def update_positions(self):
        try:
            positions = self.api.list_positions()
            logger.info(f"Active positions: {len(positions)}")
            
            for position in positions:
                current_price = float(position.current_price)
                pnl = float(position.unrealized_pl)
                pnl_percent = float(position.unrealized_plpc) * 100
                
                logger.info(f"{position.symbol}: P&L ${pnl:.2f} ({pnl_percent:.2f}%)")
                
        except Exception as e:
            logger.error(f"Error updating positions: {e}")
    
    def run(self):
        logger.info("Starting Momentum Trading Bot...")
        logger.info(f"Watching: {', '.join(self.watchlist)}")
        logger.info(f"Risk per trade: {Config.MAX_POSITION_SIZE*100}%")
        logger.info(f"Stop loss: {Config.STOP_LOSS_PERCENT*100}%")
        logger.info(f"Take profit: {Config.TAKE_PROFIT_PERCENT*100}%")
        
        while True:
            try:
                if not self.check_market_hours():
                    logger.info("Market is closed. Waiting...")
                    time.sleep(60)
                    continue
                
                self.run_scanner()
                self.update_positions()
                
                time.sleep(30)
                
            except KeyboardInterrupt:
                logger.info("Bot stopped by user")
                break
            except Exception as e:
                logger.error(f"Bot error: {e}")
                time.sleep(60)

if __name__ == "__main__":
    bot = MomentumTradingBot()
    bot.run()