"""
Historical and Real-time Fund Data Provider with Caching.
Provides:
1. Historical NAV timeseries (date, nav, acc_nav, daily_growth_pct)
2. Basic fund information (code, name, type, established date)
3. In-memory and file cache to optimize backtest speeds
"""

import httpx
import re
import json
import os
import time
from datetime import datetime, date
from typing import List, Dict, Any, Optional

# Cache directory inside DATA_DIR / cache
DATA_DIR = os.environ.get("DATA_DIR", os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
CACHE_DIR = os.path.join(DATA_DIR, "cache", "fund_history")
os.makedirs(CACHE_DIR, exist_ok=True)

# In-memory LRU cache
_MEM_CACHE: Dict[str, Dict[str, Any]] = {}
CACHE_TTL_SECONDS = 3600 * 6  # 6 hours cache during daytime


async def fetch_fund_history(fund_code: str, force_refresh: bool = False) -> Dict[str, Any]:
    """
    Fetch all historical NAV data points for a fund.
    Returns:
    {
        "code": "000001",
        "name": "华夏成长混合",
        "start_date": "2001-12-18",
        "end_date": "2026-08-25",
        "data_count": 5900,
        "history": [
            {"date": "2001-12-18", "nav": 1.0, "acc_nav": 1.0, "change_pct": 0.0},
            ...
        ]
    }
    """
    fund_code = fund_code.strip()
    now_ts = time.time()

    # 1. Check in-memory cache
    if not force_refresh and fund_code in _MEM_CACHE:
        cached = _MEM_CACHE[fund_code]
        if now_ts - cached.get("cached_at", 0) < CACHE_TTL_SECONDS:
            return cached["data"]

    # 2. Check local disk cache
    cache_file = os.path.join(CACHE_DIR, f"{fund_code}.json")
    if not force_refresh and os.path.exists(cache_file):
        try:
            mtime = os.path.getmtime(cache_file)
            if now_ts - mtime < CACHE_TTL_SECONDS:
                with open(cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    _MEM_CACHE[fund_code] = {"cached_at": mtime, "data": data}
                    return data
        except Exception as e:
            print(f"[FundDataProvider] Error reading disk cache for {fund_code}: {e}")

    # 3. Fetch from Eastmoney pingzhongdata JS
    url = f"https://fund.eastmoney.com/pingzhongdata/{fund_code}.js"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": f"https://fund.eastmoney.com/{fund_code}.html"
    }

    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            content = resp.content.decode('utf-8', errors='replace')

            name_match = re.search(r'var fS_name = \"(.*?)\";', content)
            fund_name = name_match.group(1) if name_match else fund_code

            trend_match = re.search(r'var Data_netWorthTrend = (\[.*?\]);', content)
            acc_trend_match = re.search(r'var Data_ACWorthTrend = (\[.*?\]);', content)

            if not trend_match:
                raise ValueError(f"Fund {fund_code} historical NAV trend data not found")

            net_worth_raw = json.loads(trend_match.group(1))
            acc_worth_raw = json.loads(acc_trend_match.group(1)) if acc_trend_match else []

            # Map timestamp ms to acc_nav
            acc_map = {}
            for item in acc_worth_raw:
                if isinstance(item, list) and len(item) >= 2:
                    ts, acc_val = item[0], item[1]
                    acc_map[ts] = acc_val

            history = []
            prev_nav = None
            for item in net_worth_raw:
                # item format: {"x": 1008604800000, "y": 1.0, "equityReturn": 0, "unitMoney": ""}
                ts = item.get("x")
                nav = float(item.get("y", 0.0))
                change_pct = float(item.get("equityReturn", 0.0)) if item.get("equityReturn") is not None else 0.0
                dt_str = datetime.fromtimestamp(ts / 1000.0).strftime("%Y-%m-%d")
                acc_nav = acc_map.get(ts, nav)

                if prev_nav is not None and prev_nav > 0 and change_pct == 0.0 and nav != prev_nav:
                    change_pct = round((nav - prev_nav) / prev_nav * 100.0, 4)

                history.append({
                    "date": dt_str,
                    "timestamp": ts,
                    "nav": nav,
                    "acc_nav": acc_nav,
                    "change_pct": change_pct
                })
                prev_nav = nav

            # Sort ascending by date
            history.sort(key=lambda x: x["date"])

            result = {
                "code": fund_code,
                "name": fund_name,
                "start_date": history[0]["date"] if history else "",
                "end_date": history[-1]["date"] if history else "",
                "data_count": len(history),
                "latest_nav": history[-1]["nav"] if history else 0.0,
                "history": history
            }

            # Save to disk cache and memory cache
            try:
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump(result, f, ensure_ascii=False)
            except Exception as e:
                print(f"[FundDataProvider] Error writing disk cache for {fund_code}: {e}")

            _MEM_CACHE[fund_code] = {"cached_at": now_ts, "data": result}
            return result

    except Exception as e:
        print(f"[FundDataProvider] Error fetching fund {fund_code}: {e}")
        # If cache exists even if expired, fallback to it
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        raise e


def filter_history_by_date(history: List[Dict[str, Any]], start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
    """Filter historical data list within start_date and end_date (inclusive)."""
    if not history:
        return []

    filtered = []
    for item in history:
        d = item["date"]
        if start_date and d < start_date:
            continue
        if end_date and d > end_date:
            continue
        filtered.append(item)
    return filtered
