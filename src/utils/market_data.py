#!/usr/bin/env python3
"""
Lightweight free-data helpers for classification and scoring.
Sources:
- Finnhub profile2 (market cap, beta) via FINNHUB_API_KEY/FINNHIB_API_KEY
- yfinance snapshot (price, average volume, short percent of float if available)
- yfinance options summary (nearest expiry volume)
"""

from typing import Dict, Optional
import os
import requests
import yfinance as yf


def fetch_finnhub_profile(symbol: str) -> Dict:
    api_key = os.getenv("FINNHUB_API_KEY") or os.getenv("FINNHIB_API_KEY") or ""
    if not api_key:
        return {}
    url = "https://finnhub.io/api/v1/stock/profile2"
    try:
        resp = requests.get(url, params={"symbol": symbol, "token": api_key}, timeout=15)
        if resp.status_code != 200:
            return {}
        data = resp.json() or {}
        result = {}
        # Map to our fields
        if "marketCapitalization" in data:
            result["market_cap"] = float(data.get("marketCapitalization") or 0)
        if "beta" in data:
            result["beta"] = float(data.get("beta") or 0)
        return result
    except Exception:
        return {}


def fetch_yf_snapshot(symbol: str) -> Dict:
    try:
        t = yf.Ticker(symbol)
        # Fast info block
        fast = getattr(t, "fast_info", None)
        price = None
        avg_volume = None
        if fast:
            price = getattr(fast, "last_price", None) or getattr(fast, "last_trade_price", None)
            avg_volume = getattr(fast, "ten_day_average_volume", None) or getattr(fast, "three_month_average_volume", None)
        # Legacy info dict may contain shortPercentOfFloat, sharesOutstanding
        info = {}
        try:
            info = t.info or {}
        except Exception:
            info = {}
        short_pct_float = info.get("shortPercentOfFloat") or info.get("shortPercentOfSharesOutstanding")
        shares_float = info.get("floatShares") or info.get("sharesFloat")
        return {
            "price": float(price) if price else None,
            "average_volume": float(avg_volume) if avg_volume else None,
            "short_percent_float": float(short_pct_float) * 100.0 if short_pct_float else None,
            "shares_float": float(shares_float) if shares_float else None,
        }
    except Exception:
        return {}


def fetch_yf_options_summary(symbol: str) -> Dict:
    """Summarize nearest expiry options volume. Not 'unusual flow', but indicates activity.
    Returns: {call_volume, put_volume, total_volume, call_put_ratio}
    """
    try:
        t = yf.Ticker(symbol)
        expirations = t.options or []
        if not expirations:
            return {}
        # Use nearest expiry
        expiry = expirations[0]
        chain = t.option_chain(expiry)
        calls = getattr(chain, 'calls', None)
        puts = getattr(chain, 'puts', None)
        call_vol = int(calls['volume'].fillna(0).sum()) if calls is not None else 0
        put_vol = int(puts['volume'].fillna(0).sum()) if puts is not None else 0
        total = call_vol + put_vol
        ratio = (call_vol / max(put_vol, 1)) if total > 0 else 0.0
        return {
            "call_volume": call_vol,
            "put_volume": put_vol,
            "total_volume": total,
            "call_put_ratio": float(ratio)
        }
    except Exception:
        return {}


