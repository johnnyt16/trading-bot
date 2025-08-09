#!/usr/bin/env python3
"""
Momentum, short-interest proxies, timing, and exit optimization utilities.
All methods are designed to be cheap (free data) and resilient. Missing data
is handled gracefully with defaults to avoid breaking flows.
"""

from typing import Dict, List, Tuple
from datetime import datetime, time
import yfinance as yf


def get_short_interest_signals(symbol: str) -> Dict:
    """Best-effort free proxies for short interest pressure.
    - Put/Call open interest skew from nearest expiry via yfinance
    - Social mentions placeholder (returns 0 by default)
    """
    signals: Dict = {}
    try:
        t = yf.Ticker(symbol)
        expirations = t.options or []
        if expirations:
            expiry = expirations[0]
            chain = t.option_chain(expiry)
            calls = getattr(chain, 'calls', None)
            puts = getattr(chain, 'puts', None)
            put_oi = int(getattr(puts, 'openInterest', []).sum()) if puts is not None else 0
            call_oi = int(getattr(calls, 'openInterest', []).sum()) if calls is not None else 0
            signals['put_call_oi_skew'] = float(put_oi) / max(call_oi, 1)
    except Exception:
        pass
    # Placeholder for Reddit/WSB mentions
    signals['wsb_mentions'] = 0
    return signals


class MomentumDetector:
    def __init__(self):
        pass

    @staticmethod
    def detect_opening_drive(bars) -> bool:
        """bars: pandas DataFrame 5-min bars of current session.
        Heuristic: first bar range large and volume elevated.
        """
        try:
            if bars is None or len(bars) < 1:
                return False
            first = bars.iloc[0]
            rng = float(first['high'] - first['low'])
            vol = float(first['volume'])
            avg_vol = float(bars['volume'].mean()) if len(bars) > 0 else 0
            return (rng > 0 and vol > 3 * max(avg_vol, 1))
        except Exception:
            return False

    @staticmethod
    def detect_vwap_break(bars) -> bool:
        try:
            if bars is None or bars.empty:
                return False
            # Simple VWAP approximation over bars
            typical = (bars['high'] + bars['low'] + bars['close']) / 3
            vwap = (typical * bars['volume']).cumsum() / (bars['volume'].replace(0, 1)).cumsum()
            return float(bars['close'].iloc[-1]) > float(vwap.iloc[-1])
        except Exception:
            return False

    @staticmethod
    def detect_range_expansion(bars) -> bool:
        try:
            if bars is None or len(bars) < 3:
                return False
            rng = (bars['high'] - bars['low']).iloc[-1]
            avg_rng = (bars['high'] - bars['low']).rolling(3).mean().iloc[-2]
            return float(rng) > 1.5 * float(avg_rng)
        except Exception:
            return False

    @staticmethod
    def detect_accumulation_breakout(bars) -> bool:
        try:
            if bars is None or len(bars) < 10:
                return False
            # Breakout if last close > max of prior closes
            last_close = float(bars['close'].iloc[-1])
            prior_max = float(bars['close'].iloc[-10:-1].max())
            return last_close > prior_max
        except Exception:
            return False

    def scan_all_patterns(self, bars) -> Tuple[Dict[str, bool], int]:
        signals = {
            'opening_drive': self.detect_opening_drive(bars),
            'vwap_break': self.detect_vwap_break(bars),
            'range_expansion': self.detect_range_expansion(bars),
            'accumulation_breakout': self.detect_accumulation_breakout(bars),
        }
        score = (
            (3 if signals['opening_drive'] else 0) +
            (2 if signals['vwap_break'] else 0) +
            (2 if signals['range_expansion'] else 0) +
            (1 if signals['accumulation_breakout'] else 0)
        )
        return signals, score


def optimize_entry_timing(signal_strength: int) -> str:
    """Very simple time-window recommender based on signal strength and daypart."""
    now = datetime.now().time()
    def within(start_hm: Tuple[int, int], end_hm: Tuple[int, int]) -> bool:
        s = time(start_hm[0], start_hm[1])
        e = time(end_hm[0], end_hm[1])
        return s <= now <= e
    if signal_strength >= 8:
        return 'immediate'
    if within((9, 30), (10, 0)):
        return 'opening_drive'
    if within((11, 30), (12, 30)):
        return 'lunch_reversal'
    if within((15, 0), (16, 0)):
        return 'power_hour'
    if within((4, 0), (9, 30)):
        return 'pre_market_gap'
    return 'wait'


class ExitOptimizer:
    def dynamic_exit_strategy(self, unrealized_gain_pct: float) -> Dict:
        if unrealized_gain_pct < 50.0:
            return {'action': 'hold'}
        elif unrealized_gain_pct < 100.0:
            return {'action': 'trim', 'percent': 25, 'reason': 'booking_partial'}
        elif unrealized_gain_pct < 300.0:
            return {'action': 'trim', 'percent': 50, 'reason': 'significant_gain', 'trailing_stop': 0.15}
        else:
            return {'action': 'hold_core', 'percent_to_keep': 25, 'sell_percent': 75, 'reason': 'home_run_potential', 'trailing_stop': 0.25}

    def detect_momentum_exhaustion(self, bars) -> bool:
        try:
            if bars is None or len(bars) < 5:
                return False
            vol_trend = float((bars['volume'].iloc[-5:]).mean() - (bars['volume'].iloc[-10:-5]).mean()) if len(bars) >= 10 else 0
            price_trend = float(bars['close'].iloc[-1] - bars['close'].iloc[-5])
            # Simple exhaustion if volume down and price stalling
            return (vol_trend < 0 and price_trend <= 0)
        except Exception:
            return False


