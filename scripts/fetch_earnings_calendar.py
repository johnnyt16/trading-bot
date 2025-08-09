#!/usr/bin/env python3
"""
Fetch upcoming earnings to data/earnings_calendar.csv using Finnhub (preferred),
then Yahoo fallback. FMP is not used.

Usage examples:
  # Finnhub (preferred)
  python scripts/fetch_earnings_calendar.py --days 2 --finnhub-key YOUR_FINNHUB_KEY
  # or rely on env var FINNHUB_API_KEY
  FINNHUB_API_KEY=YOUR_FINNHUB_KEY python scripts/fetch_earnings_calendar.py --days 2


Writes CSV with headers: date,symbol
"""

import os
import sys
import csv
import argparse
from datetime import datetime, timedelta
from urllib.parse import urlencode

import requests
from dotenv import load_dotenv

try:
    from loguru import logger
except Exception:  # fallback if loguru unavailable at runtime
    class _L:
        def info(self, *a, **k): print(*a)
        def warning(self, *a, **k): print(*a)
        def error(self, *a, **k): print(*a)
        def debug(self, *a, **k): print(*a)
    logger = _L()


def get_et_date_now():
    try:
        import pytz
        et = pytz.timezone('US/Eastern')
        return datetime.now(pytz.utc).astimezone(et)
    except Exception:
        return datetime.now()


def fetch_finnhub_earnings(api_key: str, days: int):
    """Fetch earnings calendar from Finnhub free endpoint for a date range."""
    et_now = get_et_date_now()
    start_date = et_now.date()
    end_date = (et_now + timedelta(days=days)).date()
    base_url = "https://finnhub.io/api/v1/calendar/earnings"
    params = {
        "from": start_date.isoformat(),
        "to": end_date.isoformat(),
        "token": api_key,
    }
    url = f"{base_url}?{urlencode(params)}"
    logger.info(f"Fetching earnings (Finnhub): {url}")
    resp = requests.get(url, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"Finnhub request failed: {resp.status_code} {resp.text[:200]}")
    data = resp.json()
    if not isinstance(data, dict) or "earningsCalendar" not in data:
        raise RuntimeError("Finnhub payload missing earningsCalendar")
    rows = []
    for item in data.get("earningsCalendar", []) or []:
        d = item.get("date")
        s = (item.get("symbol") or "").upper()
        if d and s:
            rows.append({"date": d, "symbol": s})
    return rows



def fetch_yahoo_day(date_str: str):
    """Fallback: scrape Yahoo Finance earnings calendar for a specific date.
    Returns list of symbols. No external dependencies beyond requests/regex.
    """
    import re
    url = f"https://finance.yahoo.com/calendar/earnings?day={date_str}"
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
    }
    r = requests.get(url, headers=headers, timeout=30)
    if r.status_code != 200:
        logger.warning(f"Yahoo request failed {r.status_code} for {date_str}")
        return []
    html = r.text
    # Extract ticker-like patterns from /quote/XYZ or data-symbol=\"XYZ\"
    symbols = set()
    for m in re.finditer(r"/quote/([A-Z][A-Z0-9\.\-]{0,5})\?", html):
        symbols.add(m.group(1))
    for m in re.finditer(r"data-symbol=\"([A-Z][A-Z0-9\.\-]{0,5})\"", html):
        symbols.add(m.group(1))
    return sorted(symbols)


def write_csv(rows, output_path: str):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["date", "symbol"])  # headers
        for r in rows:
            writer.writerow([r["date"], r["symbol"]])


def main():
    # Load .env so FINNHUB_API_KEY / FINNHIB_API_KEY are available without exporting
    try:
        load_dotenv()
    except Exception:
        pass
    parser = argparse.ArgumentParser(description="Fetch earnings to CSV from FMP")
    parser.add_argument("--days", type=int, default=2, help="Number of days ahead to fetch (default 2)")
    parser.add_argument(
        "--finnhub-key",
        type=str,
        default=(os.getenv("FINNHUB_API_KEY", "") or os.getenv("FINNHIB_API_KEY", "")),
        help="Finnhub API key (env: FINNHUB_API_KEY; also supports FINNHIB_API_KEY)"
    )
    parser.add_argument("--output", type=str, default=os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "earnings_calendar.csv"), help="Output CSV path")
    args = parser.parse_args()

    try:
        rows = []
        # Try Finnhub first
        if args.finnhub_key.strip():
            try:
                rows = fetch_finnhub_earnings(api_key=args.finnhub_key.strip(), days=args.days)
            except Exception as e:
                logger.warning(f"Finnhub earnings fetch failed ({e})")
        # Final fallback: Yahoo scrape
        if not rows:
            logger.warning("Falling back to Yahoo earnings scrape")
            et_now = get_et_date_now()
            for i in range(args.days + 1):
                d = (et_now + timedelta(days=i)).date().isoformat()
                symbols = fetch_yahoo_day(d)
                for s in symbols:
                    rows.append({"date": d, "symbol": s})
        # Deduplicate and sort
        dedup = {(r["date"], r["symbol"]) for r in rows}
        rows = [{"date": d, "symbol": s} for (d, s) in sorted(dedup)]

        write_csv(rows, args.output)
        logger.info(f"Wrote {len(rows)} earnings rows to {args.output}")
        return 0
    except Exception as e:
        logger.error(f"Failed to fetch/write earnings: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())


