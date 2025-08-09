#!/usr/bin/env python3
"""Debug Alpaca connection and order execution (safe test)."""

import os
import time
import argparse
from dotenv import load_dotenv
import alpaca_trade_api as tradeapi
from loguru import logger

# Load environment variables
load_dotenv()

# Get credentials
api_key = os.getenv('ALPACA_API_KEY')
secret_key = os.getenv('ALPACA_SECRET_KEY')

print("API Key:", api_key[:10] + "..." if api_key else "None")
print("Secret Key:", secret_key[:10] + "..." if secret_key else "None")

# Try different base URLs
base_urls = [
    "https://paper-api.alpaca.markets",
    "https://paper-api.alpaca.markets/",
    "https://api.alpaca.markets",
]

for base_url in base_urls:
    print(f"\nTrying base URL: {base_url}")
    try:
        api = tradeapi.REST(
            key_id=api_key,
            secret_key=secret_key,
            base_url=base_url,
            api_version='v2'
        )
        
        account = api.get_account()
        print(f"✅ SUCCESS! Connected to Alpaca")
        print(f"   Account Status: {account.status}")
        print(f"   Buying Power: ${account.buying_power}")
        print(f"   Portfolio Value: ${account.portfolio_value}")
        break
        
    except Exception as e:
        print(f"❌ Failed: {e}")

print("\nNow trying without api_version parameter:")
try:
    api = tradeapi.REST(
        api_key,
        secret_key,
        "https://paper-api.alpaca.markets"
    )
    
    account = api.get_account()
    print(f"✅ SUCCESS without api_version!")
    print(f"   Portfolio Value: ${account.portfolio_value}")
    
except Exception as e:
    print(f"❌ Failed: {e}")


def place_test_order(api: tradeapi.REST, symbol: str, qty: int, use_market: bool, do_place: bool) -> None:
    """Place a tiny test order similar to production (bracket) and cancel it.
    Will only place if do_place=True. Default uses bracket limit; market optional.
    """
    try:
        clock = api.get_clock()
        is_open = bool(getattr(clock, 'is_open', False))
        snap = api.get_snapshot(symbol, feed='iex')
        last = float(snap.latest_trade.price) if snap and snap.latest_trade else None
        if not last:
            logger.error("Could not fetch last price; aborting test order")
            return
        entry = last * (1.005 if not use_market else 1.0)
        stop = last * 0.98
        target = last * 1.02
        logger.info(f"Symbol {symbol} last={last:.2f} entry={entry:.2f} stop={stop:.2f} target={target:.2f}")
        if not do_place:
            logger.info("Dry-run only (set --place-order true to submit)")
            return
        params = dict(
            symbol=symbol,
            qty=qty,
            side='buy',
            time_in_force='day',
        )
        if use_market:
            params.update(type='market')
        else:
            params.update(type='limit', limit_price=round(entry, 2))
        # Use bracket like production when market is open (extended hours + bracket may be restricted)
        if is_open:
            params.update(order_class='bracket', stop_loss={'stop_price': round(stop, 2)}, take_profit={'limit_price': round(target, 2)})
        else:
            logger.warning("Market closed: submitting simple order (no bracket) to avoid rejection")
        logger.info(f"Submitting order: {params}")
        order = api.submit_order(**params)
        logger.info(f"Submitted: id={order.id} status={order.status}")
        time.sleep(2)
        try:
            # Attempt cancel to keep account clean
            api.cancel_order(order.id)
            logger.info("Canceled test order")
        except Exception as ce:
            logger.warning(f"Cancel failed (might have filled): {ce}")
    except Exception as e:
        logger.error(f"Order test failed: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Alpaca connectivity and order test")
    parser.add_argument('--symbol', type=str, default='AAPL')
    parser.add_argument('--qty', type=int, default=1)
    parser.add_argument('--use-market', action='store_true', help='Use market instead of limit')
    parser.add_argument('--place-order', action='store_true', help='Actually place an order')
    args = parser.parse_args()

    base_url = os.getenv('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets')
    api = tradeapi.REST(
        os.getenv('ALPACA_API_KEY'),
        os.getenv('ALPACA_SECRET_KEY'),
        base_url
    )
    logger.info(f"Testing order flow on {base_url}")
    place_test_order(api, args.symbol, args.qty, args.use_market, args.place_order)