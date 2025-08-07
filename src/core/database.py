from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
from loguru import logger

Base = declarative_base()

class Trade(Base):
    __tablename__ = 'trades'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), nullable=False)
    side = Column(String(10))  # buy/sell
    quantity = Column(Integer)
    entry_price = Column(Float)
    exit_price = Column(Float)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    entry_time = Column(DateTime, default=datetime.utcnow)
    exit_time = Column(DateTime)
    status = Column(String(20))  # open/closed/cancelled
    pnl = Column(Float)
    pnl_percent = Column(Float)
    strategy = Column(String(50))
    confidence_score = Column(Float)
    reasons = Column(JSON)  # Store signal reasons
    alpaca_order_id = Column(String(100))

class Position(Base):
    __tablename__ = 'positions'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), nullable=False)
    quantity = Column(Integer)
    avg_entry_price = Column(Float)
    current_price = Column(Float)
    unrealized_pnl = Column(Float)
    unrealized_pnl_percent = Column(Float)
    opened_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

class Performance(Base):
    __tablename__ = 'performance'
    
    id = Column(Integer, primary_key=True)
    date = Column(DateTime, default=datetime.utcnow)
    starting_balance = Column(Float)
    ending_balance = Column(Float)
    daily_pnl = Column(Float)
    daily_pnl_percent = Column(Float)
    total_trades = Column(Integer)
    winning_trades = Column(Integer)
    losing_trades = Column(Integer)
    win_rate = Column(Float)
    avg_win = Column(Float)
    avg_loss = Column(Float)
    sharpe_ratio = Column(Float)
    max_drawdown = Column(Float)

class Signal(Base):
    __tablename__ = 'signals'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    symbol = Column(String(10))
    signal_type = Column(String(10))  # buy/sell/hold
    confidence = Column(Float)
    rsi = Column(Float)
    volume_ratio = Column(Float)
    price_change_5m = Column(Float)
    price_change_1h = Column(Float)
    indicators = Column(JSON)
    executed = Column(Boolean, default=False)
    execution_price = Column(Float)

class DatabaseManager:
    def __init__(self, db_url=None):
        if db_url is None:
            db_url = os.getenv('DATABASE_URL', 'sqlite:///trading_bot.db')
        
        self.engine = create_engine(db_url, echo=False)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        logger.info(f"Database initialized: {db_url}")
    
    def add_trade(self, trade_data):
        trade = Trade(**trade_data)
        self.session.add(trade)
        self.session.commit()
        return trade.id
    
    def update_trade(self, trade_id, **kwargs):
        trade = self.session.query(Trade).filter_by(id=trade_id).first()
        if trade:
            for key, value in kwargs.items():
                setattr(trade, key, value)
            self.session.commit()
    
    def get_open_trades(self):
        return self.session.query(Trade).filter_by(status='open').all()
    
    def add_signal(self, signal_data):
        signal = Signal(**signal_data)
        self.session.add(signal)
        self.session.commit()
    
    def get_today_performance(self):
        today = datetime.utcnow().date()
        return self.session.query(Performance).filter(
            Performance.date >= today
        ).first()
    
    def calculate_performance_metrics(self):
        trades = self.session.query(Trade).filter_by(status='closed').all()
        
        if not trades:
            return {}
        
        winning_trades = [t for t in trades if t.pnl > 0]
        losing_trades = [t for t in trades if t.pnl <= 0]
        
        metrics = {
            'total_trades': len(trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': len(winning_trades) / len(trades) if trades else 0,
            'total_pnl': sum(t.pnl for t in trades),
            'avg_win': sum(t.pnl for t in winning_trades) / len(winning_trades) if winning_trades else 0,
            'avg_loss': sum(t.pnl for t in losing_trades) / len(losing_trades) if losing_trades else 0,
        }
        
        return metrics
    
    def close(self):
        self.session.close()