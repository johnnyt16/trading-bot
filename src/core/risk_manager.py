import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from loguru import logger
import yfinance as yf

class RiskManager:
    def __init__(self, max_portfolio_risk: float = 0.02, max_position_risk: float = 0.01):
        self.max_portfolio_risk = max_portfolio_risk  
        self.max_position_risk = max_position_risk    
        self.max_positions = 5
        self.max_sector_concentration = 0.4
        self.max_daily_loss = 0.05
        self.max_correlation = 0.7
        
        self.daily_losses = 0
        self.positions = {}
        self.sector_allocations = {}
        
    def calculate_position_size_kelly(self, win_rate: float, avg_win: float, avg_loss: float, 
                                     confidence: float, capital: float) -> float:
        if avg_loss == 0:
            return 0
        
        b = abs(avg_win / avg_loss)
        p = win_rate
        q = 1 - p
        
        kelly_fraction = (p * b - q) / b
        
        kelly_fraction = kelly_fraction * (confidence / 100)
        
        kelly_fraction = max(0, min(kelly_fraction, 0.25))
        
        position_size = capital * kelly_fraction * self.max_position_risk
        
        return position_size
    
    def calculate_position_size_volatility(self, symbol: str, capital: float, 
                                          stop_loss_pct: float = 0.03) -> float:
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1mo", interval="1d")
            
            if hist.empty:
                return capital * 0.01  
            
            returns = hist['Close'].pct_change().dropna()
            volatility = returns.std()
            
            atr = self.calculate_atr(hist)
            current_price = hist['Close'].iloc[-1]
            
            if atr > 0 and current_price > 0:
                atr_pct = atr / current_price
                
                risk_per_share = max(stop_loss_pct * current_price, atr)
                
                position_risk = capital * self.max_position_risk
                shares = position_risk / risk_per_share
                position_size = shares * current_price
                
                volatility_adjustment = 1 / (1 + volatility * 10)
                position_size *= volatility_adjustment
                
                return min(position_size, capital * 0.1)
            
            return capital * 0.01
            
        except Exception as e:
            logger.error(f"Error calculating position size for {symbol}: {e}")
            return capital * 0.01
    
    def calculate_atr(self, data: pd.DataFrame, period: int = 14) -> float:
        high = data['High']
        low = data['Low']
        close = data['Close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean().iloc[-1]
        
        return atr
    
    def check_correlation(self, symbol1: str, symbol2: str, period: int = 30) -> float:
        try:
            ticker1 = yf.Ticker(symbol1)
            ticker2 = yf.Ticker(symbol2)
            
            hist1 = ticker1.history(period=f"{period}d")['Close']
            hist2 = ticker2.history(period=f"{period}d")['Close']
            
            if len(hist1) < 10 or len(hist2) < 10:
                return 0
            
            returns1 = hist1.pct_change().dropna()
            returns2 = hist2.pct_change().dropna()
            
            min_len = min(len(returns1), len(returns2))
            returns1 = returns1.iloc[-min_len:]
            returns2 = returns2.iloc[-min_len:]
            
            correlation = returns1.corr(returns2)
            
            return correlation
            
        except Exception as e:
            logger.error(f"Error calculating correlation between {symbol1} and {symbol2}: {e}")
            return 0
    
    def check_portfolio_correlation(self, new_symbol: str, existing_positions: List[str]) -> bool:
        if not existing_positions:
            return True
        
        for position in existing_positions:
            correlation = self.check_correlation(new_symbol, position)
            if abs(correlation) > self.max_correlation:
                logger.warning(f"High correlation ({correlation:.2f}) between {new_symbol} and {position}")
                return False
        
        return True
    
    def calculate_var(self, positions: Dict[str, Dict], confidence_level: float = 0.95) -> float:
        if not positions:
            return 0
        
        portfolio_values = []
        for symbol, position in positions.items():
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="1mo")['Close']
                returns = hist.pct_change().dropna()
                
                position_value = position['quantity'] * position['current_price']
                position_returns = returns * position_value
                portfolio_values.append(position_returns)
                
            except Exception as e:
                logger.error(f"Error calculating VaR for {symbol}: {e}")
        
        if not portfolio_values:
            return 0
        
        portfolio_returns = pd.concat(portfolio_values, axis=1).sum(axis=1)
        
        var = np.percentile(portfolio_returns, (1 - confidence_level) * 100)
        
        return abs(var)
    
    def calculate_sharpe_ratio(self, returns: pd.Series, risk_free_rate: float = 0.02) -> float:
        if len(returns) < 2:
            return 0
        
        excess_returns = returns - risk_free_rate / 252  
        
        if returns.std() == 0:
            return 0
        
        sharpe = (excess_returns.mean() / returns.std()) * np.sqrt(252)
        
        return sharpe
    
    def check_risk_limits(self, symbol: str, position_size: float, current_positions: Dict, 
                         account_value: float) -> Tuple[bool, str]:
        if len(current_positions) >= self.max_positions:
            return False, f"Maximum positions ({self.max_positions}) reached"
        
        position_risk = position_size / account_value
        if position_risk > self.max_position_risk:
            return False, f"Position risk ({position_risk:.2%}) exceeds limit ({self.max_position_risk:.2%})"
        
        total_risk = sum(pos['value'] for pos in current_positions.values()) + position_size
        portfolio_risk = total_risk / account_value
        if portfolio_risk > self.max_portfolio_risk * len(current_positions) + 1:
            return False, f"Portfolio risk would exceed limits"
        
        if self.daily_losses / account_value > self.max_daily_loss:
            return False, f"Daily loss limit ({self.max_daily_loss:.2%}) reached"
        
        existing_symbols = list(current_positions.keys())
        if not self.check_portfolio_correlation(symbol, existing_symbols):
            return False, "Position too correlated with existing holdings"
        
        return True, "Risk check passed"
    
    def calculate_stop_loss(self, symbol: str, entry_price: float, 
                          method: str = 'atr') -> float:
        if method == 'fixed':
            return entry_price * (1 - 0.03)
        
        elif method == 'atr':
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="1mo")
                atr = self.calculate_atr(hist)
                
                stop_loss = entry_price - (2 * atr)
                
                max_loss = entry_price * 0.95
                stop_loss = max(stop_loss, max_loss)
                
                return stop_loss
                
            except Exception as e:
                logger.error(f"Error calculating ATR stop loss: {e}")
                return entry_price * 0.97
        
        elif method == 'support':
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="3mo")
                
                lows = hist['Low'].rolling(window=20).min()
                recent_support = lows.iloc[-1]
                
                stop_loss = recent_support * 0.98
                
                return max(stop_loss, entry_price * 0.95)
                
            except Exception as e:
                logger.error(f"Error calculating support stop loss: {e}")
                return entry_price * 0.97
        
        return entry_price * 0.97
    
    def calculate_take_profit(self, symbol: str, entry_price: float, 
                            stop_loss: float, risk_reward_ratio: float = 2) -> float:
        risk = entry_price - stop_loss
        
        take_profit = entry_price + (risk * risk_reward_ratio)
        
        return take_profit
    
    def update_daily_pnl(self, pnl: float) -> None:
        self.daily_losses = min(self.daily_losses + pnl, 0)
        
        if pnl < 0:
            logger.warning(f"Daily losses: ${self.daily_losses:.2f}")
    
    def reset_daily_limits(self) -> None:
        self.daily_losses = 0
        logger.info("Daily risk limits reset")
    
    def get_risk_metrics(self, positions: Dict) -> Dict:
        metrics = {
            'total_positions': len(positions),
            'daily_losses': self.daily_losses,
            'portfolio_var': self.calculate_var(positions),
            'risk_status': 'OK'
        }
        
        if self.daily_losses < -1000:
            metrics['risk_status'] = 'HIGH'
        elif self.daily_losses < -500:
            metrics['risk_status'] = 'MEDIUM'
        
        return metrics