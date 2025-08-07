from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from loguru import logger

class BaseStrategy(ABC):
    """
    Abstract base class for all trading strategies
    """
    
    def __init__(self, name: str = "BaseStrategy"):
        self.name = name
        self.positions = {}
        self.signals = []
        self.confidence_threshold = 60
        
    @abstractmethod
    def calculate_signals(self, symbol: str, data: Dict) -> Dict:
        """
        Calculate trading signals for a given symbol
        Returns: Dict with signal, confidence, and reasons
        """
        pass
    
    @abstractmethod
    def should_enter_position(self, symbol: str, data: Dict) -> bool:
        """
        Determine if we should enter a position
        """
        pass
    
    @abstractmethod
    def should_exit_position(self, symbol: str, data: Dict) -> bool:
        """
        Determine if we should exit a position
        """
        pass
    
    def execute_strategy(self, symbols: List[str], market_data: Dict) -> List[Dict]:
        """
        Execute strategy logic for multiple symbols
        Returns list of trade signals
        """
        trade_signals = []
        
        for symbol in symbols:
            if symbol not in market_data:
                continue
            
            data = market_data[symbol]
            signal = self.calculate_signals(symbol, data)
            
            if signal['confidence'] >= self.confidence_threshold:
                trade_signals.append({
                    'symbol': symbol,
                    'signal': signal,
                    'strategy': self.name
                })
                
                logger.info(f"{self.name} - {symbol}: {signal['action']} "
                          f"(confidence: {signal['confidence']}%)")
        
        return trade_signals
    
    def update_position(self, symbol: str, position_data: Dict) -> None:
        """
        Update internal position tracking
        """
        self.positions[symbol] = position_data
    
    def get_position(self, symbol: str) -> Optional[Dict]:
        """
        Get current position for a symbol
        """
        return self.positions.get(symbol)
    
    def clear_position(self, symbol: str) -> None:
        """
        Remove position from tracking
        """
        if symbol in self.positions:
            del self.positions[symbol]