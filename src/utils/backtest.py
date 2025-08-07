import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf
from loguru import logger
from typing import Dict, List, Tuple
import json
import os

class Backtester:
    def __init__(self, initial_capital: float = 10000):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.positions = {}
        self.trades = []
        self.equity_curve = []
        self.current_date = None
        
    def load_historical_data(self, symbol: str, period: str = "3mo", interval: str = "1h") -> pd.DataFrame:
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period, interval=interval)
            data['Symbol'] = symbol
            logger.info(f"Loaded {len(data)} bars for {symbol}")
            return data
        except Exception as e:
            logger.error(f"Error loading data for {symbol}: {e}")
            return pd.DataFrame()
    
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        data['SMA_20'] = data['Close'].rolling(window=20).mean()
        data['SMA_50'] = data['Close'].rolling(window=50).mean()
        
        data['RSI'] = self.calculate_rsi(data['Close'])
        
        data['Volume_Ratio'] = data['Volume'] / data['Volume'].rolling(window=20).mean()
        
        data['Returns'] = data['Close'].pct_change()
        data['Volatility'] = data['Returns'].rolling(window=20).std()
        
        data['BB_Upper'], data['BB_Middle'], data['BB_Lower'] = self.bollinger_bands(data['Close'])
        
        data['MACD'], data['MACD_Signal'], data['MACD_Hist'] = self.calculate_macd(data['Close'])
        
        return data
    
    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def bollinger_bands(self, prices: pd.Series, period: int = 20, std_dev: int = 2) -> Tuple[pd.Series, pd.Series, pd.Series]:
        middle = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        return upper, middle, lower
    
    def calculate_macd(self, prices: pd.Series) -> Tuple[pd.Series, pd.Series, pd.Series]:
        exp1 = prices.ewm(span=12, adjust=False).mean()
        exp2 = prices.ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=9, adjust=False).mean()
        histogram = macd - signal
        return macd, signal, histogram
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        data['Signal'] = 0
        data['Confidence'] = 0
        
        buy_conditions = (
            (data['RSI'] < 30) |  
            ((data['Close'] > data['SMA_20']) & (data['Volume_Ratio'] > 1.5)) |  
            (data['Close'] < data['BB_Lower'])  
        )
        
        sell_conditions = (
            (data['RSI'] > 70) |  
            (data['Close'] > data['BB_Upper'])  
        )
        
        data.loc[buy_conditions, 'Signal'] = 1
        data.loc[sell_conditions, 'Signal'] = -1
        
        confidence_scores = []
        for idx in data.index:
            score = 0
            if data.loc[idx, 'RSI'] < 30:
                score += 30
            if data.loc[idx, 'Close'] > data.loc[idx, 'SMA_20']:
                score += 20
            if data.loc[idx, 'Volume_Ratio'] > 1.5:
                score += 25
            if data.loc[idx, 'MACD_Hist'] > 0:
                score += 15
            confidence_scores.append(min(score, 100))
        
        data['Confidence'] = confidence_scores
        
        return data
    
    def execute_trade(self, symbol: str, signal: int, price: float, size: int, date: datetime) -> None:
        trade = {
            'symbol': symbol,
            'date': date,
            'signal': signal,
            'price': price,
            'size': size,
            'value': price * size
        }
        
        if signal == 1:  
            if symbol not in self.positions:
                if self.capital >= trade['value']:
                    self.positions[symbol] = {
                        'size': size,
                        'entry_price': price,
                        'entry_date': date
                    }
                    self.capital -= trade['value']
                    trade['type'] = 'BUY'
                    self.trades.append(trade)
                    logger.debug(f"BUY {symbol}: {size} @ ${price:.2f}")
        
        elif signal == -1:  
            if symbol in self.positions:
                position = self.positions[symbol]
                exit_value = price * position['size']
                pnl = exit_value - (position['entry_price'] * position['size'])
                pnl_pct = pnl / (position['entry_price'] * position['size']) * 100
                
                self.capital += exit_value
                
                trade['type'] = 'SELL'
                trade['pnl'] = pnl
                trade['pnl_pct'] = pnl_pct
                self.trades.append(trade)
                
                del self.positions[symbol]
                logger.debug(f"SELL {symbol}: {position['size']} @ ${price:.2f} | PnL: ${pnl:.2f} ({pnl_pct:.2f}%)")
    
    def run_backtest(self, symbols: List[str], start_date: str = None, end_date: str = None) -> Dict:
        logger.info(f"Starting backtest with ${self.initial_capital:,.2f}")
        
        all_data = {}
        for symbol in symbols:
            data = self.load_historical_data(symbol)
            if not data.empty:
                data = self.calculate_indicators(data)
                data = self.generate_signals(data)
                all_data[symbol] = data
        
        if not all_data:
            logger.error("No data loaded for backtest")
            return {}
        
        dates = sorted(set().union(*[set(data.index) for data in all_data.values()]))
        
        for date in dates:
            self.current_date = date
            daily_value = self.capital
            
            for symbol, data in all_data.items():
                if date in data.index:
                    row = data.loc[date]
                    
                    if row['Signal'] != 0 and row['Confidence'] > 60:
                        position_size = min(self.capital * 0.1, self.capital)  
                        shares = int(position_size / row['Close'])
                        
                        if shares > 0:
                            self.execute_trade(symbol, row['Signal'], row['Close'], shares, date)
            
            for symbol, position in self.positions.items():
                if symbol in all_data and date in all_data[symbol].index:
                    current_price = all_data[symbol].loc[date, 'Close']
                    daily_value += current_price * position['size']
            
            self.equity_curve.append({
                'date': date,
                'value': daily_value,
                'capital': self.capital,
                'positions': len(self.positions)
            })
        
        for symbol, position in list(self.positions.items()):
            if symbol in all_data:
                last_price = all_data[symbol]['Close'].iloc[-1]
                self.execute_trade(symbol, -1, last_price, position['size'], dates[-1])
        
        return self.calculate_statistics()
    
    def calculate_statistics(self) -> Dict:
        if not self.trades:
            return {
                'total_trades': 0,
                'final_capital': self.capital,
                'total_return': 0,
                'message': 'No trades executed'
            }
        
        winning_trades = [t for t in self.trades if t.get('pnl', 0) > 0]
        losing_trades = [t for t in self.trades if t.get('pnl', 0) <= 0]
        
        total_pnl = sum(t.get('pnl', 0) for t in self.trades)
        total_return = (self.capital - self.initial_capital) / self.initial_capital * 100
        
        equity_df = pd.DataFrame(self.equity_curve)
        if not equity_df.empty:
            equity_df['returns'] = equity_df['value'].pct_change()
            sharpe_ratio = (equity_df['returns'].mean() / equity_df['returns'].std()) * np.sqrt(252) if equity_df['returns'].std() > 0 else 0
            
            equity_df['cummax'] = equity_df['value'].cummax()
            equity_df['drawdown'] = (equity_df['value'] - equity_df['cummax']) / equity_df['cummax']
            max_drawdown = equity_df['drawdown'].min() * 100
        else:
            sharpe_ratio = 0
            max_drawdown = 0
        
        stats = {
            'initial_capital': self.initial_capital,
            'final_capital': self.capital,
            'total_return': total_return,
            'total_return_dollars': self.capital - self.initial_capital,
            'total_trades': len([t for t in self.trades if t['type'] == 'BUY']),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': len(winning_trades) / len([t for t in self.trades if 'pnl' in t]) * 100 if self.trades else 0,
            'avg_win': np.mean([t['pnl'] for t in winning_trades]) if winning_trades else 0,
            'avg_loss': np.mean([t['pnl'] for t in losing_trades]) if losing_trades else 0,
            'largest_win': max([t.get('pnl', 0) for t in self.trades]) if self.trades else 0,
            'largest_loss': min([t.get('pnl', 0) for t in self.trades]) if self.trades else 0,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'profit_factor': abs(sum(t['pnl'] for t in winning_trades) / sum(t['pnl'] for t in losing_trades)) if losing_trades and sum(t['pnl'] for t in losing_trades) != 0 else 0
        }
        
        return stats
    
    def save_results(self, stats: Dict, filename: str = None) -> None:
        if filename is None:
            filename = f"backtest_results/backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        results = {
            'statistics': stats,
            'trades': self.trades,
            'equity_curve': self.equity_curve
        }
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"Backtest results saved to {filename}")
    
    def print_summary(self, stats: Dict) -> None:
        print("\n" + "="*60)
        print("BACKTEST RESULTS")
        print("="*60)
        print(f"Initial Capital: ${stats['initial_capital']:,.2f}")
        print(f"Final Capital: ${stats['final_capital']:,.2f}")
        print(f"Total Return: {stats['total_return']:.2f}% (${stats['total_return_dollars']:,.2f})")
        print(f"\nTotal Trades: {stats['total_trades']}")
        print(f"Winning Trades: {stats['winning_trades']}")
        print(f"Losing Trades: {stats['losing_trades']}")
        print(f"Win Rate: {stats['win_rate']:.2f}%")
        print(f"\nAverage Win: ${stats['avg_win']:.2f}")
        print(f"Average Loss: ${stats['avg_loss']:.2f}")
        print(f"Largest Win: ${stats['largest_win']:.2f}")
        print(f"Largest Loss: ${stats['largest_loss']:.2f}")
        print(f"\nSharpe Ratio: {stats['sharpe_ratio']:.2f}")
        print(f"Max Drawdown: {stats['max_drawdown']:.2f}%")
        print(f"Profit Factor: {stats['profit_factor']:.2f}")
        print("="*60)

if __name__ == "__main__":
    backtester = Backtester(initial_capital=1000)
    
    symbols = ['TSLA', 'NVDA', 'AMD', 'AAPL', 'SPY']
    
    stats = backtester.run_backtest(symbols)
    
    backtester.print_summary(stats)
    
    backtester.save_results(stats)