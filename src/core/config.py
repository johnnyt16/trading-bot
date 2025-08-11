import os
from dotenv import load_dotenv
import alpaca_trade_api as tradeapi
from loguru import logger
import sys

load_dotenv()

# Logger configuration moved to main.py to avoid duplication
# Only configure console output here if this file is run directly
if __name__ == "__main__":
    logger.remove()
    logger.add(sys.stderr, format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}")

class Config:
    ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
    ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
    ALPACA_BASE_URL = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
    
    MAX_POSITION_SIZE = float(os.getenv("MAX_POSITION_SIZE", 0.05))
    STOP_LOSS_PERCENT = float(os.getenv("STOP_LOSS_PERCENT", 0.03))
    TAKE_PROFIT_PERCENT = float(os.getenv("TAKE_PROFIT_PERCENT", 0.05))
    MIN_CONFIDENCE_SCORE = float(os.getenv("MIN_CONFIDENCE_SCORE", 0.6))
    
    # Default to an empty watchlist unless explicitly provided via env
    WATCHLIST = [s.strip() for s in os.getenv("WATCHLIST", "").split(",") if s.strip()]

def get_alpaca_client():
    try:
        api = tradeapi.REST(
            Config.ALPACA_API_KEY,
            Config.ALPACA_SECRET_KEY,
            Config.ALPACA_BASE_URL
        )
        return api
    except Exception as e:
        logger.error(f"Failed to create Alpaca client: {e}")
        return None

def test_connection():
    logger.info("Testing Alpaca connection...")
    
    if not Config.ALPACA_API_KEY or Config.ALPACA_API_KEY == "your_api_key_here":
        logger.error("Please set your Alpaca API keys in the .env file")
        return False
    
    api = get_alpaca_client()
    if not api:
        return False
    
    try:
        account = api.get_account()
        logger.success(f"Connected to Alpaca! Account status: {account.status}")
        logger.info(f"Buying power: ${account.buying_power}")
        logger.info(f"Cash: ${account.cash}")
        logger.info(f"Portfolio value: ${account.portfolio_value}")
        return True
    except Exception as e:
        logger.error(f"Connection failed: {e}")
        return False

if __name__ == "__main__":
    test_connection()